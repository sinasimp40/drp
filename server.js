const express = require('express');
const path = require('path');
const fs = require('fs');
const archiver = require('archiver');

const app = express();
const PORT = 5000;

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

app.get('/download/launcher.bat', (req, res) => {
  const batContent = fs.readFileSync(path.join(__dirname, 'scripts', 'launcher.bat'), 'utf8');
  res.setHeader('Content-Disposition', 'attachment; filename="RobloxPortableLauncher.bat"');
  res.setHeader('Content-Type', 'application/octet-stream');
  res.send(batContent);
});

app.get('/download/setup.bat', (req, res) => {
  const batContent = fs.readFileSync(path.join(__dirname, 'scripts', 'setup.bat'), 'utf8');
  res.setHeader('Content-Disposition', 'attachment; filename="SetupPortableFolder.bat"');
  res.setHeader('Content-Type', 'application/octet-stream');
  res.send(batContent);
});

app.get('/download/all.zip', (req, res) => {
  res.setHeader('Content-Disposition', 'attachment; filename="RobloxPortableLauncher.zip"');
  res.setHeader('Content-Type', 'application/zip');

  const archive = archiver('zip', { zlib: { level: 9 } });
  archive.pipe(res);
  archive.directory(path.join(__dirname, 'scripts'), false);
  archive.file(path.join(__dirname, 'public', 'README.txt'), { name: 'README.txt' });
  archive.finalize();
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Roblox Portable Launcher running on port ${PORT}`);
});
