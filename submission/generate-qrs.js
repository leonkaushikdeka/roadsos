// QR Code Generator for RoadSoS Submission
// Run: cd submission && node generate-qrs.js
// Prerequisites: npm install qrcode

const QRCode = require('qrcode');

// Replace these URLs after deployment
const PWA_URL = 'https://roadsos.vercel.app';
const WA_URL = 'https://wa.me/+919876543210?text=SOS';

async function main() {
  try {
    await QRCode.toFile('../submission/qr-pwa.png', PWA_URL, { width: 400, margin: 2 });
    console.log('Saved: submission/qr-pwa.png');
  } catch (e) {
    console.error('Failed to generate PWA QR:', e.message);
  }

  try {
    await QRCode.toFile('../submission/qr-whatsapp.png', WA_URL, { width: 400, margin: 2 });
    console.log('Saved: submission/qr-whatsapp.png');
  } catch (e) {
    console.error('Failed to generate WhatsApp QR:', e.message);
  }
}

main();