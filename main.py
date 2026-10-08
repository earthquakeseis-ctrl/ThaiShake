from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np, time

app = FastAPI(title="ThaiShake")
client = Client("EARTHSCOPE")

STATIONS = [
    {"net":"TM","sta":"CHBT","lat":12.74,"lon":102.35},
    {"net":"TM","sta":"CMMT","lat":18.8128,"lon":98.9476},
    {"net":"TM","sta":"CMAI","lat":19.93,"lon":99.045},
    {"net":"TM","sta":"CRAI","lat":20.23,"lon":100.37},
    {"net":"TM","sta":"LOEI","lat":17.51,"lon":101.62},
    {"net":"TM","sta":"MHIT","lat":19.31,"lon":97.96},
    {"net":"TM","sta":"NAYO","lat":14.32,"lon":101.32},
    {"net":"TM","sta":"NONG","lat":18.06,"lon":103.15},
    {"net":"TM","sta":"PANO","lat":17.15,"lon":104.61},
    {"net":"TM","sta":"PBKT","lat":16.57,"lon":100.97},
    {"net":"TM","sta":"PHRA","lat":18.5,"lon":100.23},
    {"net":"TM","sta":"PRAC","lat":12.47,"lon":99.79},
    {"net":"TM","sta":"SKLT","lat":7.18,"lon":100.62},
    {"net":"TM","sta":"SRDT","lat":14.39,"lon":99.12},
    {"net":"TM","sta":"SURA","lat":9.17,"lon":99.63},
    {"net":"TM","sta":"TMDB","lat":13.67,"lon":100.61},
    {"net":"TM","sta":"UBPT","lat":15.28,"lon":105.47},
    {"net":"TM","sta":"KHLT","lat":14.797,"lon":98.589},
    {"net":"TM","sta":"NAMM","lat":6.9,"lon":100.54,"is_yours":True},
]
CACHE = {"data":None,"time":0}
ESP32 = {"pga_g":0.000015,"updated":0}

@app.get("/api/v1/shake")
def get_shake():
    global CACHE
    if CACHE["data"] and time.time()-CACHE["time"] < 60:
        for s in CACHE["data"]:
            if s["sta"]=="NAMM": s["pga_g"]=ESP32["pga_g"]
        return CACHE["data"]
    t2=UTCDateTime.now(); t1=t2-120; out=[]
    for s in STATIONS:
        if s.get("is_yours"):
            out.append({**s,"pga_g":ESP32["pga_g"],"pga_gal":ESP32["pga_g"]*980.665,"status":"ESP32 NAMM"})
            continue
        try:
            inv=client.get_stations(network=s["net"],station=s["sta"],level="response",starttime=t1,endtime=t2)
            st=client.get_waveforms(s["net"],s["sta"],"*","HHZ",t1,t2)
            st.attach_response(inv); st.remove_response(output="ACC",pre_filt=(0.1,0.2,45,50))
            pga=float(np.max(np.abs(st[0].data))/9.80665)
            if pga>1: pga=0
            out.append({**s,"pga_g":pga,"pga_gal":pga*980.665,"status":"real ACC"})
        except:
            out.append({**s,"pga_g":0,"pga_gal":0,"status":"no data"})
    CACHE={"data":out,"time":time.time()}
    return out

@app.get("/api/v1/push")
def push(pga_g: float):
    ESP32["pga_g"]=pga_g; ESP32["updated"]=time.time(); CACHE["time"]=0
    return {"ok":True}

@app.get("/manifest.json")
def manifest():
    return JSONResponse({"name":"ThaiShake","short_name":"ThaiShake","start_url":"/app","display":"standalone","background_color":"#0a192f","theme_color":"#00ff88","icons":[{"src":"https://cdn-icons-png.flaticon.com/512/3383/3383076.png","sizes":"512x512","type":"image/png"}]})

@app.get("/app", response_class=HTMLResponse)
def app_page():
    return """
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>ThaiShake 18</title><link rel="manifest" href="/manifest.json">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>body{margin:0;font-family:sans-serif;background:#0a192f;color:white}#map{height:55vh}#list{height:45vh;overflow:auto;padding:10px}
.card{background:#112240;padding:8px;margin:6px 0;border-radius:8px;display:flex;justify-content:space-between}
.green{border-left:4px solid #00ff88}.yellow{border-left:4px solid yellow}.orange{border-left:4px solid orange}.red{border-left:4px solid red}
#top{padding:10px;display:flex;justify-content:space-between}button{background:#00ff88;border:none;padding:8px 12px;border-radius:6px;font-weight:bold}</style>
</head><body><div id="top"><b>🇹🇭 ThaiShake 18 สถานี</b><button onclick="load()">Refresh</button></div>
<div id="map"></div><div id="list">Loading...</div>
<script>
var map=L.map('map').setView([13.5,100.8],5.5); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
var markers={};
function cls(g){ if(g>0.01) return 'red'; if(g>0.001) return 'orange'; if(g>0.0001) return 'yellow'; return 'green';}
function load(){
 fetch('/api/v1/shake').then(r=>r.json()).then(data=>{
  var html=''; data.sort((a,b)=>b.pga_g-a.pga_g);
  data.forEach(s=>{
   if(!markers[s.sta]) markers[s.sta]=L.circleMarker([s.lat,s.lon],{radius:10}).addTo(map);
   var c=cls(s.pga_g); var rad=s.pga_g>0?Math.max(8,Math.min(22,s.pga_g*300000+8)):6;
   markers[s.sta].setStyle({color:c,fillColor:c,fillOpacity:0.7,radius:rad}).bindPopup(`<b>${s.sta}</b><br>${s.pga_g.toExponential(2)} g`);
   html+=`<div class="card ${c}"><span><b>${s.sta}</b> <small>${s.status}</small></span><span>${s.pga_g.toExponential(2)} g</span></div>`;
  }); document.getElementById('list').innerHTML=html;
 });
}
load(); setInterval(load,60000);
</script></body></html>"""

@app.get("/")
def root(): return RedirectResponse("/app")
#add for MP
import os
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
