import asyncio
import logging
from datetime import timedelta

from pymongo.errors import DuplicateKeyError

from bson import ObjectId

from app.core.config import settings
from app.core.database import get_db, mongo_transaction
from app.modules.admin.audit import write_audit_event
from app.modules.audio.service import DEFAULT_NEURAL_VOICES, SynthResult, TranslationRateLimited, tts_service
from app.modules.audio.distributed_lease import (AudioSlotLease, HEARTBEAT_SECONDS, LEASE_SECONDS)
from app.modules.audio.source_version import source_fingerprint
from app.modules.audio.task_store import ACTIVE_STATUSES, audio_task_store, now, serialize

logger = logging.getLogger("quan4.audio.tasks")
RATE_LIMIT_RETRY_SECONDS = 100  # above the shared 90-second Google cooldown
MAX_AUTO_TRANSLATION_RETRIES = 3  # stop within ~10 min instead of silently waiting >2h
MAX_RETRY_DELAY_SECONDS = 300


def _ready_to_retry_filter(stamp):
    return {"$or": [{"retry_at": {"$exists": False}}, {"retry_at": {"$lte": stamp}}]}


class ActiveTaskExists(ValueError):
    """Quán này đã có tác vụ audio đang chờ/chạy/tạm dừng."""

    def __init__(self, task_id: str):
        super().__init__("POI đã có tác vụ audio đang xử lý")
        self.task_id = task_id


class AudioTaskManager:
    def __init__(self) -> None:
        self.max_concurrency = min(3, max(1, settings.MAX_CONCURRENT_TTS))
        self.workers: dict[str, asyncio.Task] = {}
        self._restart: set[str] = set()
        self._stopping = False
        self._semaphore: asyncio.Semaphore | None = None
        self._semaphore_loop: asyncio.AbstractEventLoop | None = None
        self._enqueue_lock: asyncio.Lock | None = None
        self._enqueue_loop: asyncio.AbstractEventLoop | None = None
        self._supervisor: asyncio.Task | None = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._semaphore is None or self._semaphore_loop is not loop:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
            self._semaphore_loop = loop
        return self._semaphore

    def _get_enqueue_lock(self) -> asyncio.Lock:
        # Serialize "find active + insert" inside one server worker to avoid double-click races.
        # Deploy with one Uvicorn worker; a multi-instance queue needs a distributed claim/lease.
        loop = asyncio.get_running_loop()
        if self._enqueue_lock is None or self._enqueue_loop is not loop:
            self._enqueue_lock = asyncio.Lock()
            self._enqueue_loop = loop
        return self._enqueue_lock

    # ------------------------------------------------------------------
    # Tạo tác vụ
    # ------------------------------------------------------------------
    async def enqueue_poi_audio_task(self, poi_id: str, languages: list[str] | None = None,
                                         *, actor_id: str | None = None, actor_ip: str | None = None) -> str:
        if not ObjectId.is_valid(poi_id):
            raise ValueError("Invalid POI ID")
        langs = list(dict.fromkeys(list(DEFAULT_NEURAL_VOICES) if languages is None else languages))
        if not langs or any(l not in DEFAULT_NEURAL_VOICES for l in langs):
            raise ValueError("Invalid languages")
        poi = await get_db()["poi"].find_one({"_id": ObjectId(poi_id)}, {"name": 1})
        if not poi:
            raise ValueError("POI not found")
        async with self._get_enqueue_lock():
            active = await audio_task_store.find_active_for_poi(poi_id)
            if active:
                raise ActiveTaskExists(str(active["_id"]))
            try:
                if actor_id is not None:
                    async with mongo_transaction() as tx:
                        task_id = await audio_task_store.create(
                            poi_id, poi.get("name", ""), langs, session=tx, notify=False,
                        )
                        await write_audit_event(
                            actor_id, "audio.task_enqueue", f"audio_task:{task_id}", actor_ip,
                            {"poi_id": poi_id, "languages": langs}, session=tx,
                        )
                    audio_task_store._notify()
                else:
                    task_id = await audio_task_store.create(poi_id, poi.get("name", ""), langs)
            except DuplicateKeyError as exc:
                # Unique partial index also enforces one active task across processes.
                active = await audio_task_store.find_active_for_poi(poi_id)
                if active:
                    raise ActiveTaskExists(str(active["_id"])) from exc
                raise
        self._start(task_id)
        return task_id

    # ------------------------------------------------------------------
    # Vòng đời worker
    # ------------------------------------------------------------------
    def _start(self, task_id: str) -> None:
        worker = self.workers.get(task_id)
        if worker and not worker.done():
            # Worker cũ còn đang kết thúc (vd: vừa Pause rồi Resume ngay) → chạy lại khi nó xong.
            self._restart.add(task_id)
            return
        self._restart.discard(task_id)
        task = asyncio.create_task(self._process(task_id), name=f"audio-task-{task_id}")
        self.workers[task_id] = task
        task.add_done_callback(lambda t, tid=task_id: self._on_done(tid, t))

    def _on_done(self, task_id: str, task: asyncio.Task) -> None:
        if self.workers.get(task_id) is task:
            self.workers.pop(task_id, None)
        if task_id in self._restart and not self._stopping:
            self._restart.discard(task_id)
            self._start(task_id)

    async def _lease_heartbeat(self, task_id: str, lease: AudioSlotLease, lost: asyncio.Event) -> None:
        """Refresh both the global slot and the task ownership while alive."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_SECONDS)
                if not await lease.refresh():
                    lost.set()
                    return
                result = await audio_task_store.collection.update_one(
                    {"_id": ObjectId(task_id), "lease_token": lease.token,
                     "status": {"$in": ["running", "paused"]}},
                    {"$set": {"lease_until": now() + timedelta(seconds=LEASE_SECONDS)}},
                )
                if not result.matched_count:
                    return  # Cancelled / already completed; the owner will release its slot.
        except asyncio.CancelledError:
            raise
        except Exception:
            lost.set()
            logger.exception("Lost audio task lease %s", task_id)

    async def _finish_transaction(self, task_id: str, token: str) -> bool:
        """Complete the task and increment dataset_version as ONE atomic commit."""
        db = get_db()
        async with mongo_transaction() as tx:
            stamp = now()
            updated = await db["audio_tasks"].update_one(
                {"_id": ObjectId(task_id), "status": "running", "lease_token": token,
                 "lease_until": {"$gt": stamp}},
                {"$set": {"status": "completed", "current_language": None,
                          "finished_at": stamp, "updated_at": stamp},
                 "$unset": {"lease_token": "", "lease_until": ""}},
                session=tx,
            )
            if not updated.matched_count:
                return False
            await db["system_meta"].update_one(
                {"_id": "dataset"},
                {"$inc": {"version": 1}, "$set": {"updated_at": stamp}},
                upsert=True, session=tx,
            )
            await write_audit_event(None, "audio.task_completed", f"audio_task:{task_id}",
                                    details={"outcome": "completed"}, session=tx)
        audio_task_store._notify()  # ONLY publish a completion after successful commit.
        return True

    async def _process(self, task_id: str) -> None:
        store = audio_task_store
        lease = AudioSlotLease()
        heartbeat = None
        lost = asyncio.Event()
        try:
            async with self._get_semaphore():
                # Global MongoDB-backed slot: at most three across ALL API processes.
                await lease.acquire()
                stamp = now()
                # Claim queued -> running atomically; only one server can win.
                claim = await store.collection.update_one(
                    {"_id": ObjectId(task_id), "status": "queued", **_ready_to_retry_filter(stamp)},
                    {"$set": {"status": "running", "error": None,
                              "started_at": stamp, "updated_at": stamp,
                              "lease_token": lease.token,
                              "lease_until": stamp + timedelta(seconds=LEASE_SECONDS)},
                     "$unset": {"retry_at": ""}},
                )
                if not claim.matched_count:
                    return
                store._notify()
                heartbeat = asyncio.create_task(self._lease_heartbeat(task_id, lease, lost))
                task = await store.get(task_id)
                poi = await get_db()["poi"].find_one({"_id": ObjectId(task["poi_id"])})
                if not poi:
                    raise ValueError("POI no longer exists")
                base = await self._base_description(poi)
                if not base:
                    raise ValueError("Missing Vietnamese description")
                fingerprint = self.source_fingerprint(poi, base)
                if task.get("source_hash") and task["source_hash"] != fingerprint:
                    raise ValueError("POI text changed; create a new audio task")
                if not task.get("source_hash"):
                    # Legacy checkpoint: without provenance, redo ALL languages safely
                    # instead of skipping any possibly stale generated translations.
                    if not await store.update_if(
                        task_id, ("running",), lease_token=lease.token,
                        source_hash=fingerprint, done=0, cache_hits=0,
                    ):
                        return

                for index, lang in enumerate(task["languages"]):
                    if lost.is_set():
                        raise RuntimeError("Audio worker lost its lease")
                    current = await store.get(task_id)
                    if not current or current["status"] != "running" or current.get("lease_token") != lease.token:
                        return
                    if index < current.get("done", 0):
                        continue
                    await store.update_if(task_id, ("running",), lease_token=lease.token,
                                          current_language=lang)
                    result = await self._process_language(
                        poi, base, lang, source_hash=fingerprint, task_id=task_id,
                        lease_token=lease.token, lease_id=lease.slot_id,
                    )
                    if lost.is_set():
                        raise RuntimeError("Audio worker lost its lease")
                    if not await store.update_if(
                        task_id, ("running", "paused"), lease_token=lease.token,
                        inc={"cache_hits": 1} if result.cache_hit else None,
                        done=index + 1, current_language=lang,
                    ):
                        return  # Cancelled / resumed from another process.

                # Paused tasks stay paused even when all languages are complete.
                await self._finish_transaction(task_id, lease.token)
        except asyncio.CancelledError:
            raise  # shutdown: lease expires/recovery resumes an abandoned claim
        except TranslationRateLimited as exc:
            # Google 429 is temporary. Keep already completed languages and
            # requeue with a due time, rather than marking the whole job failed.
            current = await store.get(task_id)
            retries = int((current or {}).get("translation_retries", 0)) + 1
            if retries > MAX_AUTO_TRANSLATION_RETRIES:
                await store.update_if(
                    task_id, ("running",), lease_token=lease.token,
                    status="failed", error="Google Translate tiếp tục giới hạn. Nhập bản dịch thủ công rồi nhấn Resume, hoặc thử lại sau.",
                    finished_at=now(), translation_retries=retries,
                )
            else:
                delay = min(RATE_LIMIT_RETRY_SECONDS * (2 ** (retries - 1)), MAX_RETRY_DELAY_SECONDS)
                await store.update_if(
                    task_id, ("running",), lease_token=lease.token,
                    status="queued", current_language=None,
                    error=str(exc), translation_retries=retries,
                    retry_at=now() + timedelta(seconds=delay),
                    unset=("lease_token", "lease_until"),
                )
                logger.warning("Google Translate rate-limited; task %s rescheduled (attempt %d)", task_id, retries)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Audio task thất bại %s", task_id)
            message = str(exc)[:300]
            if not await store.update_if(task_id, ("running",), lease_token=lease.token,
                                         status="failed", error=message, finished_at=now()):
                await store.update_if(task_id, ("paused",), lease_token=lease.token, error=message)
        finally:
            if heartbeat is not None:
                heartbeat.cancel()
                await asyncio.gather(heartbeat, return_exceptions=True)
            if lease.slot_id is not None:
                try:
                    await lease.release()
                except Exception:
                    logger.exception("Could not release audio lease %s", task_id)

    @staticmethod
    async def _base_description(poi: dict, session=None) -> str:
        # POI Master is the authoritative Vietnamese source. The vi localization
        # may be stale after an edit or owner submission; it is only a fallback.
        original = (poi.get("original_description") or poi.get("description") or "").strip()
        if original:
            return original
        vi = await get_db()["poi_localizations"].find_one(
            {"poi_id": poi["_id"], "lang": "vi"}, session=session,
        )
        return str((vi or {}).get("description") or "").strip()

    @staticmethod
    def source_fingerprint(poi: dict, base: str) -> str:
        """Track both name and source narrative, not dataset_version (unrelated POIs)."""
        return source_fingerprint(poi.get("name") or "", base)

    @staticmethod
    async def _process_language(poi: dict, base: str, lang: str, *,
                                source_hash: str | None = None,
                                task_id: str | None = None,
                                lease_token: str | None = None,
                                lease_id: str | None = None) -> SynthResult:
        """Only reuse translations derived from the CURRENT original narrative.

        Legacy localizations without source_hash have unknown provenance and
        must be translated again. New manual English edits record source_hash.
        """
        db = get_db()
        source_hash = source_hash or AudioTaskManager.source_fingerprint(poi, base)
        existing = await db["poi_localizations"].find_one({"poi_id": poi["_id"], "lang": lang})
        valid = existing is not None and existing.get("source_hash") == source_hash
        description = (existing or {}).get("description") if valid else None
        if not description:
            description = await tts_service.translate(base, lang)
        title = (existing or {}).get("title") if valid else None
        if not title or (lang != "vi" and title == poi.get("name")):
            title = await tts_service.translate(poi.get("name") or "", lang)
        if not title or not title.strip():
            raise ValueError("Missing translated POI title")
        result = await tts_service.synthesize(description, lang)
        stamp = now()

        async with mongo_transaction() as tx:
            if task_id and lease_token:
                current = await db["audio_tasks"].find_one(
                    {"_id": ObjectId(task_id), "lease_token": lease_token,
                     "lease_until": {"$gt": stamp},
                     "status": {"$in": ["running", "paused"]}}, session=tx)
                if current is None:
                    raise ValueError("Audio task was cancelled or lease lost")
                if lease_id:
                    slot = await db["audio_worker_slots"].find_one(
                        {"_id": lease_id, "token": lease_token,
                         "expires_at": {"$gt": stamp}}, session=tx)
                    if slot is None:
                        raise ValueError("Audio global worker slot lease lost")
            latest_poi = await db["poi"].find_one({"_id": poi["_id"]}, session=tx)
            if (not latest_poi
                    or latest_poi.get("revision", 0) != poi.get("revision", 0)
                    or latest_poi.get("name") != poi.get("name")
                    or latest_poi.get("original_description") != poi.get("original_description")):
                raise ValueError("POI changed while generating audio; please queue a new task")
            latest_base = await AudioTaskManager._base_description(latest_poi, session=tx)
            if AudioTaskManager.source_fingerprint(latest_poi, latest_base) != source_hash:
                raise ValueError("Vietnamese narrative changed while generating audio")
            latest = await db["poi_localizations"].find_one(
                {"poi_id": poi["_id"], "lang": lang}, session=tx)
            if (latest is None) != (existing is None) or (
                existing is not None and (
                    latest.get("description") != existing.get("description")
                    or latest.get("title") != existing.get("title")
                    or latest.get("source_hash") != existing.get("source_hash")
                )
            ):
                raise ValueError("Localization was edited while generating audio")
            await db["poi_localizations"].update_one(
                {"poi_id": poi["_id"], "lang": lang},
                {"$set": {
                    "title": title, "description": description,
                    "audio_url": result.url, "audio_status": "completed",
                    "source_hash": source_hash,
                    "translation_origin": "manual" if valid and existing.get("translation_origin") == "manual" else "auto",
                    "is_fallback": False, "updated_at": stamp,
                }, "$setOnInsert": {"created_at": stamp}},
                upsert=True, session=tx,
            )
            await db["poi"].update_one({"_id": poi["_id"]},
                {"$set": {"updated_at": stamp}}, session=tx)
        return result

    # ------------------------------------------------------------------
    # Pause / Resume / Cancel
    # ------------------------------------------------------------------
    async def control(self, task_id: str, action: str, *,
                      actor_id: str | None = None, actor_ip: str | None = None):
        if actor_id is not None:
            return await self._control_with_audit(task_id, action, actor_id, actor_ip)
        task = await audio_task_store.get(task_id)
        if not task:
            return None
        status = task["status"]
        if action == "pause" and status in ("queued", "running"):
            ok = await audio_task_store.update_if(task_id, ("queued", "running"), status="paused")
        elif action == "resume" and status in ("paused", "failed"):
            ok = await audio_task_store.update_if(task_id, ("paused", "failed"), status="queued", error=None,
                                                   translation_retries=0, unset=("retry_at",))
            if ok:
                self._start(task_id)
        elif action == "retry" and status == "queued" and task.get("retry_at"):
            ok = await audio_task_store.update_if(
                task_id, ("queued",), error=None, unset=("retry_at",),
            )
            if ok:
                self._start(task_id)
        elif action == "cancel" and status in ACTIVE_STATUSES + ("failed",):
            ok = await audio_task_store.update_if(
                task_id, ACTIVE_STATUSES + ("failed",), status="cancelled", current_language=None, finished_at=now()
            )
            # Stop an in-flight translation/TTS immediately rather than continuing to persist
            # localisation content after the user cancels. Shutdown uses the same semantics.
            if ok:
                worker = self.workers.get(task_id)
                if worker and not worker.done():
                    worker.cancel()
        else:
            ok = False
        if not ok:
            raise ValueError("Invalid status transition")
        return serialize(await audio_task_store.get(task_id))

    async def _control_with_audit(self, task_id: str, action: str, actor_id: str, actor_ip: str | None):
        """Change task state and append the actor's audit event in ONE transaction.

        The optimistic filter prevents two concurrent controls from both reporting
        success. Side effects (start worker, cancel worker, SSE) run after commit.
        """
        if not ObjectId.is_valid(task_id):
            return None
        db = get_db()
        transition = None
        async with mongo_transaction() as tx:
            doc = await db["audio_tasks"].find_one({"_id": ObjectId(task_id)}, session=tx)
            if doc is None:
                return None
            old = doc["status"]
            if action == "pause" and old in ("queued", "running"):
                new, fields = "paused", {"status": "paused"}
            elif action == "resume" and old in ("paused", "failed"):
                new, fields = "queued", {"status": "queued", "error": None, "translation_retries": 0}
            elif action == "retry" and old == "queued" and doc.get("retry_at"):
                new, fields = "queued", {"status": "queued", "error": None}
            elif action == "cancel" and old in ACTIVE_STATUSES + ("failed",):
                new, fields = "cancelled", {"status": "cancelled", "current_language": None,
                                             "finished_at": now()}
            else:
                raise ValueError("Invalid status transition")
            result = await db["audio_tasks"].update_one(
                {"_id": ObjectId(task_id), "status": old},
                {"$set": {**fields, "updated_at": now()},
                 **({"$unset": {"retry_at": "", "finished_at": ""}} if new == "queued" else {})}, session=tx,
            )
            if not result.matched_count:
                raise ValueError("Task was already changed by another admin")
            await write_audit_event(
                actor_id, f"audio.task_{action}", f"audio_task:{task_id}", actor_ip,
                {"poi_id": doc.get("poi_id"), "from_status": old, "to_status": new},
                session=tx,
            )
            transition = new
        audio_task_store._notify()
        if transition == "queued":
            self._start(task_id)
        elif transition == "cancelled":
            worker = self.workers.get(task_id)
            if worker and not worker.done():
                worker.cancel()
        return serialize(await audio_task_store.get(task_id))

    # ------------------------------------------------------------------
    # Recovery & shutdown
    # ------------------------------------------------------------------
    async def recover(self) -> int:
        """Recover ONLY expired claims; do not steal a running task from another worker."""
        purged = await audio_task_store.purge_finished(settings.AUDIO_TASK_RETENTION_DAYS)
        stamp = now()
        reclaimed = await get_db()["audio_tasks"].update_many(
            {"status": "running", "$or": [
                {"lease_until": {"$lte": stamp}}, {"lease_until": {"$exists": False}},
            ]},
            {"$set": {"status": "queued", "recovered_at": stamp, "updated_at": stamp},
             "$unset": {"lease_token": "", "lease_until": ""}},
        )
        ids = [str(t["_id"]) async for t in get_db()["audio_tasks"]
               .find({"status": "queued", **_ready_to_retry_filter(stamp)}, {"_id": 1}).sort("created_at", 1)]
        for task_id in ids:
            self._start(task_id)  # multiple app processes are safe: only one atomic claim wins
        # Supervisor chạy mỗi HEARTBEAT_SECONDS (15 giây). Khi hàng đợi rỗng,
        # đây là heartbeat bình thường chứ không phải một sự kiện đáng ghi INFO.
        recovered_count = reclaimed.modified_count
        if recovered_count or purged:
            logger.info(
                "Audio recovery: khôi phục %d tác vụ hết lease, %d đang chờ, dọn %d tác vụ cũ",
                recovered_count, len(ids), purged,
            )
        else:
            logger.debug("Audio recovery idle: %d tác vụ đang chờ", len(ids))
        return len(ids)

    def start_supervisor(self) -> None:
        """Continuously reclaim tasks whose owner crashed after startup."""
        if self._supervisor is None or self._supervisor.done():
            self._supervisor = asyncio.create_task(self._supervisor_loop(), name="audio-supervisor")

    async def _supervisor_loop(self) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            try:
                await self.recover()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Temporary Mongo disconnects must not permanently stop recovery.
                logger.exception("Audio supervisor will retry recovery")

    async def shutdown(self) -> None:
        self._stopping = True
        if self._supervisor is not None:
            self._supervisor.cancel()
            await asyncio.gather(self._supervisor, return_exceptions=True)
            self._supervisor = None
        workers = list(self.workers.values())
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        self.workers.clear()
        self._restart.clear()
        self._stopping = False


audio_task_manager = AudioTaskManager()
