import fitz
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import os

class CoordsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = """
            <html>
            <body style="font-family: sans-serif; text-align: center;">
            <h2>Step 1: Coordinate Configurator</h2>
            <p>Click on the image below exactly where the following text should begin.<br>
            <i>(Tip: Click slightly above the line so text sits on it, as if placing the top-left corner of the word)</i></p>
            <h3 id="instr" style="color:red; font-size: 24px;">Click where 'date' should go</h3>
            <form id="coordForm" method="POST" action="/save">
                <input type="hidden" name="data" id="data">
            </form>
            <img src="/image.png" id="pdfimg" style="border:2px solid black; cursor:crosshair; max-width: 100%;">
            <script>
                const fields = [
                    "date", "time_from", "time_to", "department", "designation", 
                    "my_space", "tasks_carried_out_today", "key_learnings_observations", 
                    "tools_technology_used", "special_achievements"
                ];
                let currentIdx = 0;
                let coords = {};
                let img = document.getElementById("pdfimg");
                let instr = document.getElementById("instr");
                img.onclick = function(e) {
                    let rect = img.getBoundingClientRect();
                    // Calculate relative x and y taking into account CSS scaling
                    let scaleX = img.naturalWidth / rect.width;
                    let scaleY = img.naturalHeight / rect.height;
                    let x = (e.clientX - rect.left) * scaleX;
                    let y = (e.clientY - rect.top) * scaleY;
                    
                    // ReportLab uses bottom-left as origin (0,0)
                    let reportlab_y = img.naturalHeight - y;
                    
                    coords[fields[currentIdx]] = {x: Math.round(x), y: Math.round(reportlab_y)};
                    currentIdx++;
                    if(currentIdx < fields.length) {
                        instr.innerText = "Click where '" + fields[currentIdx] + "' should go";
                    } else {
                        document.getElementById("data").value = JSON.stringify(coords);
                        document.getElementById("coordForm").submit();
                    }
                }
            </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        elif self.path == '/image.png':
            try:
                doc = fitz.open("OJL_pdf.pdf")
                pix = doc[0].get_pixmap(dpi=150)
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.end_headers()
                self.wfile.write(pix.tobytes("png"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                print(e)

    def do_POST(self):
        if self.path == '/save':
            length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(length).decode('utf-8')
            parsed = urllib.parse.parse_qs(post_data)
            coords_json = parsed['data'][0]
            with open("overlay_coords.json", "w") as f:
                f.write(coords_json)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            success_html = "<h2>Successfully saved overlay_coords.json! 🎉</h2><h3>You can now close this tab, hit Ctrl+C in your terminal, and run `python generate.py`!</h3>"
            self.wfile.write(success_html.encode('utf-8'))

def main():
    if not os.path.exists("OJL_pdf.pdf"):
        print("Error: OJL_pdf.pdf not found in the current directory.")
        return
        
    print("Starting visual coordinate configurator...")
    print("An interface will open in your web browser. Please click on the PDF to set the locations.")
    server = HTTPServer(('localhost', 8085), CoordsHandler)
    webbrowser.open('http://localhost:8085')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nConfigurator stopped.")

if __name__ == "__main__":
    main()
