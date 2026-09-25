// Extrae window.DATA de un chat_*.js a JSON (para transcripciones).
global.window = {};
require(require('path').resolve(process.argv[2]));
console.log(JSON.stringify(window.DATA));
