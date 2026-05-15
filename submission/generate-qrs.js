const QRCode = require('qrcode');
const PWA_URL = 'https://roadsos.vercel.app';
const WA_URL = 'https://wa.me/+919876543210?text=SOS';

QRCode.toFile('../submission/qr-pwa.png', PWA_URL, { width: 400, margin: 2 }, function(err) {
  if (err) { console.error('PWA QR error:', err.message); process.exit(1); }
  console.log('Saved: submission/qr-pwa.png');
  QRCode.toFile('../submission/qr-whatsapp.png', WA_URL, { width: 400, margin: 2 }, function(err) {
    if (err) { console.error('WA QR error:', err.message); process.exit(1); }
    console.log('Saved: submission/qr-whatsapp.png');
  });
});