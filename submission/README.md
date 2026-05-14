import { QRCodeSVG } from 'qrcode.react';
import React, { useState } from 'react';

export default function QRGenerator() {
  const [pwaUrl, setPwaUrl] = useState('https://roadsos.vercel.app');
  const [whatsappNumber, setWhatsappNumber] = useState('+919876543210');

  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>RoadSoS QR Codes for Submission</h1>

      <div style={{ display: 'flex', gap: '3rem', marginTop: '2rem' }}>
        <div>
          <h2>PWA Link</h2>
          <input
            type="text"
            value={pwaUrl}
            onChange={(e) => setPwaUrl(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', marginBottom: '1rem' }}
          />
          <QRCodeSVG value={pwaUrl} size={256} level="H" />
        </div>

        <div>
          <h2>WhatsApp SOS Link</h2>
          <input
            type="text"
            value={whatsappNumber}
            onChange={(e) => setWhatsappNumber(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', marginBottom: '1rem' }}
          />
          <QRCodeSVG
            value={`https://wa.me/${whatsappNumber.replace('+', '')}?text=SOS`}
            size={256}
            level="H"
          />
        </div>
      </div>

      <p style={{ marginTop: '2rem', color: '#666' }}>
        Save these QR codes as PNG images for the submission folder.
      </p>
    </div>
  );
}