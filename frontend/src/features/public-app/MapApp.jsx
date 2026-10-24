import React, { useState } from 'react';
import SplashScreen from './components/SplashScreen.jsx';
import MapView from './components/MapView.jsx';
import POIDetailSheet from './components/POIDetailSheet.jsx';
import AudioPlayerBar from './components/AudioPlayerBar.jsx';
import OfflinePackModal from './components/OfflinePackModal.jsx';

/**
 * MapApp — Giao diện chính dành cho Du khách (Public Tourist PWA).
 * Phụ trách: Bảo (Nhánh `feature/tourist-pwa`)
 */
export default function MapApp() {
  const [showSplash, setShowSplash] = useState(true);
  const [showOfflineModal, setShowOfflineModal] = useState(false);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-100">
      {showSplash && <SplashScreen onComplete={() => setShowSplash(false)} />}

      <MapView onOpenOfflinePacks={() => setShowOfflineModal(true)} />
      <POIDetailSheet />
      <AudioPlayerBar />

      {showOfflineModal && (
        <OfflinePackModal onClose={() => setShowOfflineModal(false)} />
      )}
    </div>
  );
}
