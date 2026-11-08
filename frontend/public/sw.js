// Gỡ service worker PWA đã được đăng ký tại URL này trong các bản web cũ.
self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.registration.unregister());
});
