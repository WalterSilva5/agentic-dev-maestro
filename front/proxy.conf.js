// Proxy de desenvolvimento do `ng serve`: encaminha /api -> backend NestJS.
// Assim o config.json usa URL relativa ("/api") e a porta do backend NÃO fica
// hardcoded — basta exportar MAESTRO_API_PORT (ou MAESTRO_API_TARGET) ao subir.
//   ex.: MAESTRO_API_PORT=5099 npm start
const target =
  process.env.MAESTRO_API_TARGET ||
  `http://localhost:${process.env.MAESTRO_API_PORT || 5000}`;

module.exports = [
  {
    context: ['/api'],
    target,
    secure: false,
    changeOrigin: true,
    logLevel: 'debug'
  }
];
