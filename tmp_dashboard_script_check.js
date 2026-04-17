const fs = require('fs');
const script = fs.readFileSync('tmp_dashboard_inline.js', 'utf8');
new Function(script);
console.log('ok');
