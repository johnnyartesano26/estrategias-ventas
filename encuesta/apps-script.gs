// Pegar esto en: script.google.com → Nuevo proyecto
// Implementar como Aplicacion web → Ejecutar como yo → Cualquiera
// La primera vez que reciba datos, crea el Sheet automaticamente

function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  var sheet = getOrCreateSheet();

  sheet.appendRow([
    data.timestamp || new Date().toISOString(),
    data.nombre || 'Anonimo',
    data.cliente_id || '',
    data.cliente_nombre || '',
    data.canal || '',
    data.nps,
    data.calidad_cerveza,
    data.atencion_servicio,
    data.musica_sonido || '',
    data.rec_musica || '',
    data.comida || '',
    data.rec_comida || '',
    data.higiene || '',
    data.feedback || ''
  ]);

  return ContentService.createTextOutput(JSON.stringify({ ok: true, sheet: sheet.getParent().getUrl() }))
    .setMimeType(ContentService.MimeType.JSON);
}

function getOrCreateSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss && ss.getName().indexOf('Encuesta Madre Monte') >= 0) return ss.getActiveSheet();

  // Buscar si ya existe
  var files = DriveApp.getFilesByName('Encuesta Madre Monte');
  if (files.hasNext()) {
    return SpreadsheetApp.open(files.next()).getActiveSheet();
  }

  // Crear nuevo Sheet con encabezados
  ss = SpreadsheetApp.create('Encuesta Madre Monte');
  var sheet = ss.getActiveSheet();
  sheet.appendRow([
    'Timestamp', 'Nombre', 'Cliente ID', 'Cliente Nombre', 'Canal',
    'NPS', 'Calidad Cerveza', 'Atencion Servicio',
    'Musica Sonido', 'Rec Musica', 'Comida', 'Rec Comida', 'Higiene', 'Feedback'
  ]);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, 14);
  return sheet;
}

function doGet() {
  return ContentService.createTextOutput('Encuesta Madre Monte activa');
}
