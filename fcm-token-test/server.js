const http = require('http');
const fs = require('fs');
const path = require('path');

const root = __dirname;
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8' };

http.createServer((req, res) => {
  const requested = req.url === '/' ? '/index.html' : req.url;
  const file = path.resolve(root, `.${requested}`);
  if (!file.startsWith(root + path.sep)) {
    res.writeHead(403); res.end('Forbidden'); return;
  }
  fs.readFile(file, (error, data) => {
    if (error) { res.writeHead(404); res.end('Not found'); return; }
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(8765, '127.0.0.1', () => console.log('FCM token test server: http://127.0.0.1:8765'));
