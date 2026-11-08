import React, { useRef } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { FiX } from 'react-icons/fi';

export default function OwnerDialog({ open, onClose, title, description, busy, children, footer, illustration, className = "" }) {
  const returnFocus = useRef(null);
  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next && !busy) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="owner-dialog-overlay" />
        <Dialog.Content className={["owner-dialog", footer && "owner-dialog-with-footer", className].filter(Boolean).join(" ")} onOpenAutoFocus={() => {
          returnFocus.current = document.activeElement;
        }} onCloseAutoFocus={(event) => {
          if (returnFocus.current instanceof HTMLElement && returnFocus.current.isConnected) {
            event.preventDefault();
            returnFocus.current.focus();
          }
        }}>
          <header className="owner-dialog-header">
            <div>
              {illustration}
              <Dialog.Title>{title}</Dialog.Title>
              <Dialog.Description>{description}</Dialog.Description>
            </div>
            <Dialog.Close className="owner-header-action" disabled={busy} aria-label="Đóng"><FiX aria-hidden="true" /></Dialog.Close>
          </header>
          {children && <div className="owner-dialog-body">{children}</div>}
          {footer && <footer className="owner-dialog-footer">{footer}</footer>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
