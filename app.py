"""
app.py - Simple web interface.

Run:   python app.py
Open:  http://127.0.0.1:5000
Enter company name + link -> download the Word report.
"""

import os

from flask import Flask, render_template_string, request, send_file

from main import run

app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Company Info to Word</title>
<style>
  body{font-family:Segoe UI,Arial,sans-serif;background:#f3f5f9;margin:0;display:flex;
       justify-content:center;align-items:center;min-height:100vh}
  .card{background:#fff;padding:36px 40px;border-radius:14px;box-shadow:0 6px 24px rgba(0,0,0,.08);
        width:420px}
  h1{margin:0 0 6px;font-size:22px;color:#1f3a68}
  p.sub{margin:0 0 22px;color:#666;font-size:14px}
  label{display:block;font-size:13px;font-weight:600;margin:14px 0 6px;color:#333}
  input{width:100%;padding:11px 12px;border:1px solid #cfd6e2;border-radius:8px;font-size:15px;
        box-sizing:border-box}
  button{margin-top:22px;width:100%;padding:12px;border:0;border-radius:8px;background:#1f5fd1;
         color:#fff;font-size:16px;cursor:pointer}
  button:disabled{background:#8aa6d8}
  .err{background:#fde8e8;color:#a33;padding:10px;border-radius:8px;margin-top:16px;font-size:14px}
</style>
</head>
<body>
<form class="card" method="post" onsubmit="b.disabled=true;b.innerText='Scraping... please wait'">
  <h1>Company → Word Report</h1>
  <p class="sub">Enter a company name and website. We'll scan the site and build a .docx file.</p>
  <label>Company name</label>
  <input name="name" required placeholder="e.g. Acme Corporation" value="{{name}}">
  <label>Website link</label>
  <input name="url" required placeholder="e.g. https://acme.com" value="{{url}}">
  <label>Max pages to scan</label>
  <input name="pages" type="number" min="1" max="50" value="{{pages}}">
  <button id="b">Generate Word File</button>
  {% if error %}<div class="err">{{error}}</div>{% endif %}
</form>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"].strip()
        url = request.form["url"].strip()
        pages = int(request.form.get("pages") or 10)
        try:
            path = run(name, url, pages)
            return send_file(os.path.abspath(path), as_attachment=True)
        except Exception as e:
            return render_template_string(PAGE, name=name, url=url, pages=pages, error=str(e))
    return render_template_string(PAGE, name="", url="", pages=10, error=None)


if __name__ == "__main__":
    app.run(debug=True)
