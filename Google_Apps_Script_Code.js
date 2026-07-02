function doPost(e) {
  try {
    if (!e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "Không có dữ liệu payload."
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Parse JSON payload gửi lên từ Github Actions
    var payload = JSON.parse(e.postData.contents);
    var targetSheetName = payload.sheet_name;
    var rows = payload.rows;
    var clearData = payload.clear;
    
    if (!targetSheetName || !rows || !rows.length) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "Payload thiếu sheet_name hoặc mảng rows."
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Mở bảng tính đang chứa script này
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(targetSheetName);
    
    // Nếu tab không tồn tại, tự động tạo mới
    if (!sheet) {
      sheet = ss.insertSheet(targetSheetName);
    }
    
    // Nếu cờ clear = true, tiến hành xóa toàn bộ dữ liệu cũ
    if (clearData) {
      sheet.clearContents();
    }
    
    // Ghi dữ liệu mới vào sheet
    // getRange(dòng bắt đầu, cột bắt đầu, số dòng, số cột)
    sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
    
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success",
      "message": "Đã ghi " + rows.length + " dòng vào tab " + targetSheetName
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error",
      "message": error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
