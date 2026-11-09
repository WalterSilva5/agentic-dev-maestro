// Proxy de desenvolvimento do `ng serve`: encaminha /api -> backend NestJS.
// Assim o config.json usa URL relativa ("/api") e a porta do backend NÃO fica
// hardcoded — basta exportar RELAY_API_PORT (ou RELAY_API_TARGET) ao subir.
//   ex.: RELAY_API_PORT=5099 npm start
const target =
  process.env.RELAY_API_TARGET ||
  process.env.MAESTRO_API_TARGET ||
  `http://localhost:${process.env.RELAY_API_PORT || process.env.MAESTRO_API_PORT || 5000}`;

module.exports = [
  {
    context: ['/api'],
    target,
    secure: false,
    changeOrigin: true,
    logLevel: 'debug'
  }
];
