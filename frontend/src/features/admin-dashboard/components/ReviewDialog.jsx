import React, { useRef } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { FiX } from 'react-icons/fi';

export default function ReviewDialog({ title, description, busy, onClose, children, footer, widthClass = 'max-w-4xl' }) {
  const returnFocus = useRef(null);
  return (
    <Dialog.Root open onOpenChange={(open) => { if (!open && !busy) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/55" />
        <Dialog.Content
          className={`fixed left-1/2 top-1/2 z-50 flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-xl bg-white text-slate-900 shadow-xl ${widthClass}`}
          onOpenAutoFocus={() => { returnFocus.current = document.activeElement; }}
          onCloseAutoFocus={(event) => {
            if (returnFocus.current instanceof HTMLElement && returnFocus.current.isConnected) {
              event.preventDefault();
              returnFocus.current.focus();
            }
          }}
        >
          <header className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 px-4 py-4 sm:px-6">
            <div className="min-w-0">
              <Dialog.Title className="break-words text-lg font-bold">{title}</Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-slate-600">{description}</Dialog.Description>
            </div>
            <Dialog.Close type="button" aria-label="Đóng" disabled={busy}
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 disabled:opacity-40">
              <FiX aria-hidden="true" size={20} />
            </Dialog.Close>
          </header>
          <div className="min-h-0 overflow-y-auto overscroll-contain px-4 py-5 [scrollbar-color:#cbd5e1_transparent] [scrollbar-width:thin] sm:px-6">
            {children}
          </div>
          {footer && <footer className="shrink-0 border-t border-slate-200 bg-slate-50 px-4 py-4 sm:px-6">{footer}</footer>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
