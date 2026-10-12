from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np, time, os, threading
app = FastAPI(title="ThaiShake 41")
CLIENTS = {"GE": Client("GEOFON")}
def get_client(net): return CLIENTS.get(net, Client("EARTHSCOPE"))
#Stations add CH
STATIONS = [
    {"net":"TM","sta":"CHBT","lat":12.74,"lon":102.35,"chan":"HHZ"},
    {"net":"TM","sta":"CMMT","lat":18.8128,"lon":98.9476,"chan":"HHZ"},
    {"net":"TM","sta":"CMAI","lat":19.93,"lon":99.045,"chan":"HHZ"},
    {"net":"TM","sta":"CRAI","lat":20.23,"lon":100.37,"chan":"HHZ"},
    {"net":"TM","sta":"LOEI","lat":17.51,"lon":101.62,"chan":"HHZ"},
    {"net":"TM","sta":"MHIT","lat":19.31,"lon":97.96,"chan":"HHZ"},
    {"net":"TM","sta":"NAYO","lat":14.32,"lon":101.32,"chan":"HHZ"},
    {"net":"TM","sta":"NONG","lat":18.06,"lon":103.15,"chan":"HHZ"},
    {"net":"TM","sta":"PANO","lat":17.15,"lon":104.61,"chan":"HHZ"},
    {"net":"TM","sta":"PBKT","lat":16.57,"lon":100.97,"chan":"HHZ"},
    {"net":"TM","sta":"PHRA","lat":18.5,"lon":100.23,"chan":"HHZ"},
    {"net":"TM","sta":"PRAC","lat":12.47,"lon":99.79,"chan":"HHZ"},
    {"net":"TM","sta":"SKLT","lat":7.18,"lon":100.62,"chan":"HHZ"},
    {"net":"TM","sta":"SRDT","lat":14.39,"lon":99.12,"chan":"HHZ"},
    {"net":"TM","sta":"SURA","lat":9.17,"lon":99.63,"chan":"HHZ"},
    {"net":"TM","sta":"TMDB","lat":13.67,"lon":100.61,"chan":"HHZ"},
    {"net":"TM","sta":"UBPT","lat":15.28,"lon":105.47,"chan":"HHZ"},
    {"net":"TM","sta":"SRIT","lat":8.595,"lon":99.601,"chan":"HHZ"},
    {"net":"MY","sta":"KUM","lat":5.29,"lon":100.64,"chan":"BHZ"},
    {"net":"MY","sta":"IPM","lat":4.47,"lon":101.02,"chan":"BHZ"},
    {"net":"MY","sta":"KOM","lat":1.792,"lon":103.846,"chan":"BHZ"},
    {"net":"MY","sta":"KTM","lat":5.328,"lon":103.135,"chan":"HNZ"},
    {"net":"MY","sta":"FRM","lat":3.23,"lon":101.63,"chan":"HNZ"},
    {"net":"MM","sta":"SIM","lat":20.1332,"lon":92.885,"chan":"HHZ"},
    {"net":"MM","sta":"NGU","lat":21.205,"lon":94.916,"chan":"HHZ"},
    {"net":"MM","sta":"HKA","lat":22.642,"lon":93.599,"chan":"HHZ"},
    {"net":"MM","sta":"MDY","lat":22.016,"lon":96.112,"chan":"HHZ"},
    {"net":"MM","sta":"TGI","lat":20.76,"lon":97.03,"chan":"HHZ"},
    {"net":"MM","sta":"TMU","lat":24.2296,"lon":94.300,"chan":"HHZ"},
    {"net":"MM","sta":"KTA","lat":24.179,"lon":96.340,"chan":"HHZ"},
    {"net":"MM","sta":"YGN","lat":16.864,"lon":96.153,"chan":"HHZ"},
    {"net":"MM","sta":"KTN","lat":21.285,"lon":99.589,"chan":"HHZ"},
    {"net":"PS","sta":"VIVO","lat":18.65,"lon":105.70,"chan":"BHZ"},
    {"net":"GE","sta":"LHMI","lat":5.2288,"lon":96.9472,"chan":"BHZ"},
    {"net":"IN","sta":"PBA","lat":11.6557,"lon":92.743919,"chan":"HHZ"},
    {"net":"PS","sta":"PSI","lat":2.6938,"lon":98.923,"chan":"BHZ"},
    {"net":"GE","sta":"GSI","lat":1.3039,"lon":97.5755,"chan":"BHZ"},
    {"net":"GE","sta":"NPW","lat":19.778,"lon":96.137,"chan":"HHZ"},
    {"net":"RM","sta":"DLV","lat":11.952,"lon":108.481,"chan":"HHZ"},
    {"net":"RM","sta":"SLV","lat":21.325,"lon":103.906,"chan":"HHZ"},
    {"net":"TM","sta":"NAMOM","lat":6.9,"lon":100.54,"is_yours":True,"chan":"HHZ"},
]
CACHE = {"data":None,"time":0}
ESP32 = {"pga_g":0.000015,"updated":0}
def fetch_all():
    global CACHE
    t2=UTCDateTime.now(); t1=t2-300
    out=[]
    for s in STATIONS:
        if s.get("is_yours"):
            out.append({**s,"pga_g":ESP32["pga_g"],"pga_gal":ESP32["pga_g"]*980.665,"status":"ESP32 NAMOM"})
            continue
        try:
            c = get_client(s["net"])
            inv=c.get_stations(network=s["net"],station=s["sta"],level="response",starttime=t1,endtime=t2)
            chan = s.get("chan","HHZ")
            st=c.get_waveforms(s["net"],s["sta"],"*",chan,t1,t2)
            st.attach_response(inv)
            st.remove_response(output="ACC",pre_filt=(0.1,0.2,45,50))
            pga=float(np.max(np.abs(st[0].data))/9.80665)
            if pga>1: pga=0.00001
            out.append({**s,"pga_g":pga,"pga_gal":pga*980.665,"status":"ONLINE"})
        except Exception as e:
            print(f"FAIL {s['sta']} {e}")
            out.append({**s,"pga_g":None,"pga_gal":0,"status":"OFFLINE"})
    CACHE={"data":out,"time":time.time()}
@app.get("/api/v1/shake")
def get_shake(force: int = 0):
    if force==1:
        CACHE["time"]=0 # สั่งให้หมดอายุ
        threading.Thread(target=fetch_all, daemon=True).start()
        if CACHE["data"]:
            return CACHE["data"] # ส่งของเก่าไปก่อน ไม่ต้องรอ

    if CACHE["data"]:
        if time.time()-CACHE["time"] > 30: # ลดเหลือ 30 วิตามที่คุณตั้งใน JS
            threading.Thread(target=fetch_all, daemon=True).start()
        for s in CACHE["data"]:
            if s["sta"]=="NAMOM":
                s["pga_g"]=ESP32["pga_g"]
                s["pga_gal"]=ESP32["pga_g"]*980.665
        return CACHE["data"]

    # คนแรก
    temp=[]
    for s in STATIONS:
        if s.get("is_yours"):
            temp.append({**s,"pga_g":ESP32["pga_g"],"pga_gal":ESP32["pga_g"]*980.665,"status":"ESP32 NAMOM"})
        else:
            temp.append({**s,"pga_g":None,"pga_gal":0,"status":"loading..."})
    CACHE["data"]=temp
    CACHE["time"]=time.time()-70
    threading.Thread(target=fetch_all, daemon=True).start()
    return temp
@app.get("/api/v1/push")
def push(pga_g: float):
    ESP32["pga_g"]=pga_g
    ESP32["updated"]=time.time()
    CACHE["time"]=0
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
    return """<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ThaiShake 41</title><link rel="manifest" href="/manifest.json"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>body{margin:0;font-family:sans-serif;background:#0a192f;color:white}#map{height:58vh}#list{height:42vh;overflow:auto;padding:10px}.card{background:#112240;padding:6px;margin:4px 0;border-radius:6px;display:flex;justify-content:space-between;font-size:13px}#top{padding:8px;display:flex;justify-content:space-between;align-items:center}button{background:#00ff88;border:none;padding:6px 10px;border-radius:5px;font-weight:bold;cursor:pointer}.legend{background:rgba(255,255,255,0.95);color:#111;padding:8px 10px;border-radius:8px;line-height:18px;font-size:11px}.legend i{width:12px;height:12px;float:left;margin-right:6px;border-radius:50%;margin-top:2px}.watermark-gulf{font-size:48px;font-weight:900;color:rgba(0,255,136,0.18);transform:rotate(-18deg);font-family:Arial Black,sans-serif;letter-spacing:6px;white-space:nowrap;pointer-events:none}</style></head><body><div id="top"><b>🇹🇭 ThaiShake 41 - NAMOM V6</b><button onclick="load(true)">🔄 Refresh</button><span id="count"></span></div><div id="map"></div><div id="list">Loading 41 stations...</div><script>
var map=L.map('map').setView([13.2,101.0],5.8);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);var markers={};
function getColor(g){if(g==null) return "#6b7d93";var gal=g*980.665;if(gal<2.9) return "#00C853";if(gal<29.4) return "#FFD600";if(gal<60.7) return "#FF9100";if(gal<200.9) return "#FF4500";if(gal<392) return "#FF0000";return "#8B0000";}
function load(force=false){var url='/api/v1/shake'+(force?'?force=1&t='+Date.now():'');fetch(url).then(r=>r.json()).then(data=>{var html='';data.sort((a,b)=>(b.pga_g||-1)-(a.pga_g||-1));document.getElementById('count').innerText=data.length+' stations';data.forEach(s=>{var rad=s.sta=="NAMOM"?14:8;if(!markers[s.sta]) markers[s.sta]=L.circleMarker([s.lat,s.lon],{radius:rad}).addTo(map);var c=getColor(s.pga_g);var isOff=s.pga_g==null;markers[s.sta].setStyle({fillColor:c,color:isOff?"#4a5a6b":c,weight:1,fillOpacity:0.9,radius:rad}).bindPopup(`<b>${s.sta}</b><br>${s.pga_g!=null?s.pga_g.toExponential(2)+' g':'OFFLINE'}<br>${s.status}`);html+=`<div class="card" style="border-left:4px solid ${c}"><span><b>${s.sta}</b> <small>${s.status}</small></span><span style="color:${c}"><b>${s.pga_g!=null?s.pga_g.toExponential(2)+' g':'OFFLINE'}</b></span></div>`;});document.getElementById('list').innerHTML=html;});}
load();setInterval(()=>load(false),30000);
var gulfIcon=L.divIcon({className:'',html:'<div class="watermark-gulf">ThaiShake NAMOM</div>',iconSize:[460,50],iconAnchor:[230,25]});L.marker([10.8,100.7],{icon:gulfIcon,interactive:false}).addTo(map);
var legend=L.control({position:'bottomright'});legend.onAdd=function(){var d=L.DomUtil.create('div','legend');d.innerHTML='<b>PGA (gal)</b><br><i style="background:#00C853"></i>0-2.9 ปกติ<br><i style="background:#FFD600"></i>2.9-29.4 รู้สึก<br><i style="background:#FF9100"></i>29.4-60.7 สั่น<br><i style="background:#FF4500"></i>60.7-200.9 แรง<br><i style="background:#FF0000"></i>200.9-392 เสียหาย<br><i style="background:#8B0000"></i>>392 วิกฤติ<br><i style="background:#6b7d93"></i>OFFLINE';return d;};legend.addTo(map);
</script></body></html>"""
@app.get("/")
def root(): return RedirectResponse("/app")
if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
