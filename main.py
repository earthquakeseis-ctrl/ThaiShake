from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np, time, os

app = FastAPI(title="ThaiShake 41")
client = Client("EARTHSCOPE")

STATIONS = [
# --- 18 สถานี TM กรมอุตุฯ ไทย (ของจริง) ---
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

# --- 8 สถานี MY มาเลเซีย (รอบๆ ใต้ไทย) ---
{"net":"MY","sta":"KUM","lat":5.29,"lon":100.64},
{"net":"MY","sta":"IPM","lat":4.58,"lon":101.07},
{"net":"MY","sta":"KOM","lat":5.32,"lon":103.13},
{"net":"MY","sta":"KGM","lat":6.30,"lon":100.20},
{"net":"MY","sta":"BTM","lat":3.05,"lon":101.72},
{"net":"MY","sta":"KUMS","lat":5.80,"lon":100.48},
{"net":"MY","sta":"PYSM","lat":6.13,"lon":100.38},
{"net":"MY","sta":"SIJM","lat":2.81,"lon":101.50},

# --- 5 สถานี MM พม่า ---
{"net":"MM","sta":"HLE","lat":20.86,"lon":96.60},
{"net":"MM","sta":"MTA","lat":21.97,"lon":96.08},
{"net":"MM","sta":"TAU","lat":16.79,"lon":96.15},
{"net":"MM","sta":"KWA","lat":17.64,"lon":96.47},
{"net":"MM","sta":"TGI","lat":20.78,"lon":96.91},

# --- 5 สถานี GE / IU / II ภาคพื้นเอเชีย ---
{"net":"GE","sta":"LKW","lat":8.44,"lon":99.78},
{"net":"GE","sta":"SUST","lat":13.35,"lon":101.0},
{"net":"IU","sta":"CHTO","lat":18.79,"lon":98.97},
{"net":"II","sta":"KAPI","lat":11.74,"lon":99.62},
{"net":"IU","sta":"BKB","lat":11.05,"lon":99.33},

# --- 5 สถานีเพิ่มเติมรอบไทย + ของคุณ ---
{"net":"TH","sta":"CHTO","lat":18.79,"lon":98.97},
{"net":"TM","sta":"PYYM","lat":8.41,"lon":98.52},
{"net":"TM","sta":"NTAM","lat":16.77,"lon":100.15},
{"net":"TM","sta":"SRIM","lat":13.20,"lon":99.90},
{"net":"TM","sta":"NAMOM","lat":6.9,"lon":100.54,"is_yours":True},
]
CACHE = {"data":None,"time":0}
ESP32 = {"pga_g":0.000015,"updated":0}

@app.get("/api/v1/shake")
def get_shake():
    global CACHE
    if CACHE["data"] and time.time()-CACHE["time"] < 60:
        for s in CACHE["data"]:
            if s["sta"]=="NAMOM": s["pga_g"]=ESP32["pga_g"]
        return CACHE["data"]
    t2=UTCDateTime.now(); t1=t2-120; out=[]
    for s in STATIONS:
        if s.get("is_yours"):
            out.append({**s,"pga_g":ESP32["pga_g"],"pga_gal":ESP32["pga_g"]*980.665,"status":"ESP32 NAMOM"})
            continue
        try:
            inv=client.get_stations(network=s["net"],station=s["sta"],level="response",starttime=t1,endtime=t2)
            st=client.get_waveforms(s["net"],s["sta"],"*","HHZ",t1,t2)
            st.attach_response(inv); st.remove_response(output="ACC",pre_filt=(0.1,0.2,45,50))
            pga=float(np.max(np.abs(st[0].data))/9.80665)
            if pga>1: pga=0
            out.append({**s,"pga_g":pga,"pga_gal":pga*980.665,"status":"real ACC"})
        except:
            out.append({**s,"pga_g":None,"pga_gal":0,"status":"offline"})
    CACHE={"data":out,"time":time.time()}
    return out

@app.get("/api/v1/push")
def push(pga_g: float):
    ESP32["pga_g"]=pga_g; ESP32["updated"]=time.time(); CACHE["time"]=0
    return {"ok":True}

@app.get("/manifest.json")
def manifest():
    return JSONResponse({"name":"ThaiShake 41","short_name":"ThaiShake","start_url":"/app","display":"standalone","background_color":"#0a192f","theme_color":"#00ff88","icons":[{"src":"/icon.png","sizes":"512x512","type":"image/png"}]})

@app.get("/icon.png")
def get_icon():
    if os.path.exists("icon.png"): return FileResponse("icon.png")
    return RedirectResponse("https://cdn-icons-png.flaticon.com/512/3383/3383076.png")

@app.get("/app", response_class=HTMLResponse)
def app_page():
    return """
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>ThaiShake 41 Stations</title><link rel="manifest" href="/manifest.json">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
body{margin:0;font-family:sans-serif;background:#0a192f;color:white}#map{height:58vh}#list{height:42vh;overflow:auto;padding:10px}
.card{background:#112240;padding:6px;margin:4px 0;border-radius:6px;display:flex;justify-content:space-between;font-size:13px}
.green{border-left:4px solid #00C853}.yellow{border-left:4px solid #FFD600}.orange{border-left:4px solid #FF9100}.red{border-left:4px solid #FF4500}.darkred{border-left:4px solid #FF0000}.black{border-left:4px solid #2F2F2F}
#top{padding:8px;display:flex;justify-content:space-between;align-items:center}button{background:#00ff88;border:none;padding:6px 10px;border-radius:5px;font-weight:bold}
.legend{background:rgba(255,255,255,0.88);color:#111;padding:8px 10px;border-radius:8px;line-height:18px;font-size:11px;border:none;box-shadow:0 0 6px rgba(0,0,0,0.2)}
.legend i{width:12px;height:12px;float:left;margin-right:6px;border-radius:50%;margin-top:2px}
.watermark-gulf{font-size:48px;font-weight:900;color:rgba(0,255,136,0.18);transform:rotate(-18deg);font-family:Arial Black,Arial,sans-serif;letter-spacing:6px;white-space:nowrap;pointer-events:none}
</style>
</head><body>
<div id="top"><b>🇹🇭 ThaiShake 41 Stations - NAMOM v4</b><button onclick="load()">🔄 Refresh</button><span id="count" style="font-size:12px"></span></div>
<div id="map"></div><div id="list">Loading 41 stations...</div>
<script>
var map=L.map('map').setView([13.2,101.0],5.8);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
var markers={};
function getColor(g){
 if(g==null) return "#2F2F2F";
 var gal = g*980.665;
 if(gal<2.9) return "#00C853";
 if(gal<29.4) return "#FFD600";
 if(gal<60.7) return "#FF9100";
 if(gal<200.9) return "#FF4500";
 if(gal<392) return "#FF0000";
 return "#8B0000";
}
function getCls(g){
 if(g==null) return "black";
 var gal = g*980.665;
 if(gal<2.9) return "green";
 if(gal<29.4) return "yellow";
 if(gal<60.7) return "orange";
 if(gal<200.9) return "red";
 return "darkred";
}
function load(){
 fetch('/api/v1/shake').then(r=>r.json()).then(data=>{
  var html=''; data.sort((a,b)=>(b.pga_g||-1)-(a.pga_g||-1));
  document.getElementById('count').innerText = data.length+' stations';
  data.forEach(s=>{
   var rad=8; if(s.sta=="NAMOM") rad=14;
   if(!markers[s.sta]) markers[s.sta]=L.circleMarker([s.lat,s.lon],{radius:rad}).addTo(map);
   var c=getColor(s.pga_g); var cls=getCls(s.pga_g);
   markers[s.sta].setStyle({fillColor:c, color:c, weight:0, fillOpacity:0.9, radius:rad, stroke:false})
  .bindPopup(`<b>${s.sta}</b><br>${s.pga_g!=null?s.pga_g.toExponential(2)+' g':'offline'}<br>${s.status}`);
   var pgaText = s.pga_g!=null? s.pga_g.toExponential(2)+' g' : 'offline';
   html+=`<div class="card ${cls}"><span><b>${s.sta}</b> <small>${s.status}</small></span><span style="color:${c}"><b>${pgaText}</b></span></div>`;
  });
  document.getElementById('list').innerHTML=html;
 });
}
load(); setInterval(load,60000);

// Watermark กันแอบอ้างกลางอ่าวไทย
var gulfIcon = L.divIcon({className:'', html:'<div class="watermark-gulf">ThaiShake NAMOM</div>', iconSize:[460,50], iconAnchor:[230,25]});
L.marker([10.8, 100.7], {icon:gulfIcon, interactive:false, keyboard:false}).addTo(map);

// Legend พื้นขาว 7 ระดับ + offline
var legend = L.control({position:'bottomright'});
legend.onAdd = function(){
 var div = L.DomUtil.create('div','legend');
 div.innerHTML = '<b>PGA (gal)</b><br>'+
 '<i style="background:#00C853"></i> 0-2.9 เขียว ปลอดภัย<br>'+
 '<i style="background:#FFD600"></i> 2.9-29.4 เหลือง รู้สึกได้<br>'+
 '<i style="background:#FF9100"></i> 29.4-60.7 ส้ม เริ่มแรง<br>'+
 '<i style="background:#FF4500"></i> 60.7-200.9 ส้มแดง แรง<br>'+
 '<i style="background:#FF0000"></i> 200.9-392 แดง แรงมาก<br>'+
 '<i style="background:#8B0000"></i> >392 เข้ม อันตรายรุนแรง<br>'+
 '<i style="background:#2F2F2F"></i> offline เทาดำ';
 return div;
};
legend.addTo(map);
</script></body></html>
"""
@app.get("/")
def root(): return RedirectResponse("/app")
if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
