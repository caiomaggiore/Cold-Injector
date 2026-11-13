import network
import socket
import ujson
import uselect

from config import AP_SSID, wifi_password_ok

MDNS_HOST = "partida-frio"
HTTP_TIMEOUT_MS = 0

STYLE = """
:root{
  --bg:#f4f6f8;--card:#fff;--text:#1f2937;--muted:#6b7280;
  --teal:#14b8a6;--teal-dark:#0d9488;--line:#e5e7eb;
  --green:#22c55e;--red:#ef4444;--shadow:0 .125rem .5rem rgba(15,23,42,.08);
}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--text);padding:1rem;padding-bottom:2rem}
.wrap{max-width:480px;margin:0 auto}
h1{font-size:1.25rem;margin:.25rem 0 .15rem;font-weight:700}
.sub{color:var(--muted);font-size:.85rem;margin:0 0 1rem}
.nav{display:flex;gap:.35rem;margin:0 0 1rem}
.nav button{flex:1 1 0;min-width:0;border:0;text-align:center;color:var(--text);font-weight:700;
  font-size:.82rem;background:#fff;border-radius:.75rem;padding:.7rem .2rem;box-shadow:var(--shadow);cursor:pointer}
.nav button.on{background:var(--teal);color:#fff}
.page{display:none;min-height:70vh}
.page.on{display:block}
.card{background:var(--card);border-radius:1rem;box-shadow:var(--shadow);
  padding:1rem 1.1rem;margin-bottom:1rem}
.card h2{font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);margin:0 0 .75rem;font-weight:700}
.row{display:flex;align-items:center;justify-content:space-between;gap:.75rem;
  padding:.55rem 0;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0;padding-bottom:0}
.row span.lbl{font-weight:600}
.state{font-size:1.15rem;font-weight:700;margin:0}
.led{width:16px;height:16px;border-radius:50%;flex-shrink:0;
  box-shadow:inset 0 1px 2px rgba(0,0,0,.2)}
.led.on{background:var(--green);box-shadow:0 0 0 3px rgba(34,197,94,.25)}
.led.off{background:var(--red);box-shadow:0 0 0 3px rgba(239,68,68,.2)}
.toggle{appearance:none;-webkit-appearance:none;width:52px;height:30px;border:0;
  border-radius:999px;background:#d1d5db;position:relative;cursor:pointer;
  transition:background .2s;flex-shrink:0}
.toggle::after{content:"";position:absolute;top:3px;left:3px;width:24px;height:24px;
  background:#fff;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.2);
  transition:transform .2s}
.toggle:checked{background:var(--teal)}
.toggle:checked::after{transform:translateX(22px)}
.slide label{display:flex;justify-content:space-between;font-weight:600;margin:.85rem 0 .35rem}
.slide label b{color:var(--teal-dark);font-variant-numeric:tabular-nums}
input[type=range]{width:100%;accent-color:var(--teal);height:1.4rem}
.hint{font-size:.8rem;color:var(--muted);margin:.35rem 0 0}
.seg{display:flex;gap:3px;background:#eef1f4;border-radius:.75rem;padding:3px;margin:.25rem 0 .5rem}
.seg label{flex:1 1 0;margin:0;min-width:0}
.seg input{position:absolute;opacity:0;pointer-events:none}
.seg span{display:block;text-align:center;padding:.7rem .25rem;border-radius:.6rem;
  font-size:.8rem;font-weight:700;color:var(--muted);line-height:1.2;white-space:nowrap}
.seg input:checked+span{background:#fff;color:var(--text);box-shadow:var(--shadow)}
.btn{width:100%;border:0;border-radius:.75rem;padding:.85rem 1rem;margin-top:.75rem;
  font-size:1rem;font-weight:700;background:var(--teal);color:#fff;cursor:pointer;
  display:block;text-align:center;text-decoration:none}
.btn:active{background:var(--teal-dark)}
.btn-ghost{background:#eef1f4;color:var(--text)}
.btn-ghost:active{background:#e5e7eb}
.preset-lbl{display:block;font-weight:600;margin:.75rem 0 .35rem;font-size:.9rem}
.preset-lbl input,.preset-lbl select{width:100%;margin-top:.35rem;padding:.7rem .75rem;
  border:1px solid var(--line);border-radius:.7rem;font-size:1rem;background:#fff}
.kb-box{margin:.75rem 0 .35rem}
.kb-box .lbl-k{display:block;font-weight:600;font-size:.9rem}
.kb-box input{width:100%;margin-top:.35rem;padding:.7rem .75rem;
  border:1px solid var(--line);border-radius:.7rem;font-size:1rem;background:#fff;
  pointer-events:none}
.kb-box.open input{pointer-events:auto}
.msg{font-size:.85rem;color:var(--teal-dark);min-height:1.2em;margin:.4rem 0 0}
.pwm{font-size:.9rem;color:var(--muted);margin:.4rem 0 0}
.list{list-style:none;padding:0;margin:0}
.list li{padding:.7rem 0;border-bottom:1px solid var(--line);font-weight:600}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.9rem;word-break:break-all}
"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>Partida Fria</title>
<style>""" + STYLE + """</style>
</head>
<body>
<div class="wrap">
  <h1>Partida Fria</h1>
  <p class="sub" id="sub">Controle no celular</p>
  <div class="nav">
    <button type="button" id="tab-ctrl" class="on" onclick="showPage('ctrl')">Controle</button>
    <button type="button" id="tab-presets" onclick="showPage('presets')">Presets</button>
    <button type="button" id="tab-ajuste" onclick="showPage('ajuste')">Ajuste</button>
  </div>

  <div id="page-ctrl" class="page on">
    <div class="card">
      <h2>Monitor</h2>
      <p class="state" id="state">...</p>
      <div class="row"><span class="lbl">Pos-chave</span><span id="ledPost" class="led off"></span></div>
      <div class="row"><span class="lbl">Partida</span><span id="ledStart" class="led off"></span></div>
      <p class="pwm">Potencia atual: <b id="pwmNow">0</b>%</p>
      <p class="msg" id="msgCtrl"></p>
    </div>
    <div class="card">
      <h2>Sistema</h2>
      <div class="row">
        <span class="lbl">Ligado</span>
        <input class="toggle" type="checkbox" id="enabled"/>
      </div>
      <p class="hint" style="margin-top:.75rem">Quando injetar</p>
      <div class="seg">
        <label><input type="radio" name="trig" value="start" checked/><span>Partida</span></label>
        <label><input type="radio" name="trig" value="post_key"/><span>Pos-chave</span></label>
      </div>
      <p class="hint" id="delayHint"></p>
    </div>
    <div class="card">
      <h2>Ajustes</h2>
      <div class="slide">
        <label>Delay <b id="vDelay">200 ms</b></label>
        <input type="range" id="delay_ms" min="0" max="2000" step="50"/>
      </div>
      <div class="slide">
        <label>Tempo de injecao <b id="vInj">1500 ms</b></label>
        <input type="range" id="inject_ms" min="50" max="5000" step="50"/>
      </div>
      <div class="slide">
        <label>Potencia de injecao <b id="vPwm">100%</b></label>
        <input type="range" id="pwm_percent" min="0" max="100" step="1"/>
      </div>
      <button class="btn" type="button" onclick="saveFlash()">Salvar</button>
      <button class="btn btn-ghost" type="button" onclick="testInj()">Testar injecao</button>
    </div>
  </div>

  <div id="page-presets" class="page" inert>
    <div class="card">
      <h2>Configuracao atual</h2>
      <p id="now">...</p>
    </div>
    <div class="card">
      <h2>Salvar como preset</h2>
      <div class="kb-box" data-for="presetTag">
        <span class="lbl-k">Titulo do preset</span>
        <input id="presetTag" class="kb" type="text" maxlength="20" placeholder="Ex: Frio manha"
          name="preset_tag" autocomplete="off" autocapitalize="off" autocorrect="off"
          spellcheck="false" enterkeyhint="done" inputmode="text" tabindex="-1" readonly disabled/>
      </div>
      <button class="btn" type="button" onclick="savePreset()">Salvar preset</button>
      <p class="msg" id="msgPreset"></p>
    </div>
    <div class="card">
      <h2>Salvos</h2>
      <ul class="list" id="list"></ul>
    </div>
  </div>

  <div id="page-ajuste" class="page" inert>
    <div class="card">
      <h2>Como entrar</h2>
      <div class="row"><span class="lbl">Rede</span><span class="mono" id="ssid">...</span></div>
      <p class="hint">Depois de conectar, o celular deve abrir esta tela sozinho (portal da rede).</p>
      <p class="hint">Se nao abrir, use:</p>
      <p class="mono" id="url">http://partida-frio.local/</p>
    </div>
    <div class="card">
      <h2>Senha do Wi-Fi</h2>
      <span class="preset-lbl">Senha atual</span>
      <p class="mono" id="pwNow">...</p>
      <div class="kb-box" data-for="pw">
        <span class="lbl-k">Nova senha (8 a 63 caracteres)</span>
        <input id="pw" class="kb" type="text" maxlength="63" name="wifi_key"
          autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"
          enterkeyhint="done" inputmode="text" tabindex="-1" readonly disabled/>
      </div>
      <div class="kb-box" data-for="pw2">
        <span class="lbl-k">Confirmar nova senha</span>
        <input id="pw2" class="kb" type="text" maxlength="63" name="wifi_key2"
          autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"
          enterkeyhint="done" inputmode="text" tabindex="-1" readonly disabled/>
      </div>
      <button class="btn" type="button" onclick="saveWifi()">Salvar senha</button>
      <p class="msg" id="msgWifi"></p>
      <p class="hint">Depois de salvar, o celular desconecta. Entre de novo na rede Cold-Start-Injector com a senha nova.</p>
    </div>
  </div>
</div>
<script>
let saveT=null, loaded=false, wifiLoaded=false, kbOpen=null;
const SUB={
  ctrl:'Controle no celular',
  presets:'Copia a config atual. Carregar joga no save principal.',
  ajuste:'Rede Wi-Fi e senha'
};
function closeKb(){
  document.querySelectorAll('input.kb').forEach(el=>{
    el.blur();
    el.setAttribute('readonly','readonly');
    el.disabled=true;
    el.tabIndex=-1;
    const box=el.closest('.kb-box');
    if(box) box.classList.remove('open');
  });
  kbOpen=null;
}
function openKb(el){
  if(!el) return;
  document.querySelectorAll('input.kb').forEach(x=>{
    if(x!==el){
      x.blur();
      x.setAttribute('readonly','readonly');
      x.disabled=true;
      x.tabIndex=-1;
      const b=x.closest('.kb-box');
      if(b) b.classList.remove('open');
    }
  });
  el.disabled=false;
  el.removeAttribute('readonly');
  el.tabIndex=0;
  const box=el.closest('.kb-box');
  if(box) box.classList.add('open');
  kbOpen=el;
  setTimeout(function(){el.focus()},30);
}
function showPage(name){
  closeKb();
  ['ctrl','presets','ajuste'].forEach(n=>{
    const page=document.getElementById('page-'+n);
    const on=n===name;
    page.classList.toggle('on', on);
    document.getElementById('tab-'+n).classList.toggle('on', n===name);
    if(on) page.removeAttribute('inert');
    else page.setAttribute('inert','');
  });
  document.getElementById('sub').textContent=SUB[name]||'';
  if(name==='presets'){showNow();fill()}
  if(name==='ajuste') loadWifi();
}
function msg(id,t){document.getElementById(id).textContent=t||''}
function hint(mode){
  document.getElementById('delayHint').textContent=
    mode==='post_key'
      ? 'Delay: espera depois de ligar a chave (pos-chave) para comecar a injetar.'
      : 'Delay: espera depois de apertar o botao de partida para comecar a injetar.';
}
function led(id,on){const e=document.getElementById(id);e.className='led '+(on?'on':'off')}
function trig(){const r=document.querySelector('input[name=trig]:checked');return r?r.value:'start'}
function setTrig(v){document.querySelectorAll('input[name=trig]').forEach(x=>x.checked=x.value===v);hint(v)}
function vals(){
  document.getElementById('vDelay').textContent=document.getElementById('delay_ms').value+' ms';
  document.getElementById('vInj').textContent=document.getElementById('inject_ms').value+' ms';
  document.getElementById('vPwm').textContent=document.getElementById('pwm_percent').value+'%';
}
function payload(){
  return {
    enabled:document.getElementById('enabled').checked,
    delay_ms:+document.getElementById('delay_ms').value,
    inject_ms:+document.getElementById('inject_ms').value,
    pwm_percent:+document.getElementById('pwm_percent').value,
    trigger_mode:trig()
  };
}
async function j(u,opt){const r=await fetch(u,opt);return r.json()}
function applyForm(s){
  document.getElementById('enabled').checked=!!s.enabled;
  document.getElementById('delay_ms').value=s.delay_ms;
  document.getElementById('inject_ms').value=s.inject_ms;
  document.getElementById('pwm_percent').value=s.pwm_percent;
  setTrig(s.trigger_mode||'start');
  vals();
}
function paintMonitor(s){
  document.getElementById('state').textContent=s.state;
  led('ledPost',s.post_key);led('ledStart',s.start);
  document.getElementById('pwmNow').textContent=s.pwm;
}
function modo(m){return m==='post_key'?'Pos-chave':'Partida'}
function paintNow(s){
  document.getElementById('now').textContent=
    'Delay '+s.delay_ms+' ms · Injecao '+s.inject_ms+' ms · Potencia '+s.pwm_percent+'% · '+modo(s.trigger_mode);
}
async function refresh(){
  try{
    const s=await j('/api/status');
    paintMonitor(s);
    paintNow(s);
    if(!loaded){applyForm(s);loaded=true}
  }catch(e){}
}
async function live(){
  vals();
  try{await j('/api/live',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())})}catch(e){}
}
async function saveFlash(){
  try{
    await j('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});
    msg('msgCtrl','Configuracao atual salva.');
  }catch(e){msg('msgCtrl','Falha ao salvar.')}
}
async function testInj(){await j('/api/test',{method:'POST'});refresh()}
async function showNow(){
  try{paintNow(await j('/api/status'))}catch(e){}
}
async function fill(){
  try{
    const d=await j('/api/presets');
    const ul=document.getElementById('list');
    ul.innerHTML='';
    (d.items||[]).forEach(p=>{
      const li=document.createElement('li');
      li.innerHTML=p.name+'<br><span class="hint">'+p.delay_ms+' ms · '+p.inject_ms+' ms · '+p.pwm_percent+'% · '+modo(p.trigger_mode)+'</span>';
      const b1=document.createElement('button');
      b1.className='btn'; b1.textContent='Carregar no save principal';
      b1.onclick=()=>loadP(p.name);
      const b2=document.createElement('button');
      b2.className='btn btn-ghost'; b2.textContent='Apagar';
      b2.onclick=()=>delP(p.name);
      li.appendChild(b1); li.appendChild(b2);
      ul.appendChild(li);
    });
    if(!(d.items||[]).length) ul.innerHTML='<li class="hint">Nenhum preset ainda.</li>';
  }catch(e){}
}
async function savePreset(){
  const tag=document.getElementById('presetTag').value.trim();
  if(!tag){msg('msgPreset','Digite um titulo.');return}
  await j('/api/presets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:tag})});
  document.getElementById('presetTag').value='';
  closeKb();
  msg('msgPreset','Preset salvo a partir da config atual.');
  fill();
}
async function loadP(name){
  const s=await j('/api/presets/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name})});
  if(s.ok===false){msg('msgPreset','Nao encontrado.');return}
  applyForm(s);
  loaded=true;
  paintNow(s);
  msg('msgPreset','Carregado no save principal.');
}
async function delP(name){
  await j('/api/presets/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name})});
  msg('msgPreset','Apagado.');
  fill();
}
async function loadWifi(){
  try{
    const s=await j('/api/wifi');
    document.getElementById('ssid').textContent=s.ssid||'';
    document.getElementById('pwNow').textContent=s.password||'';
    document.getElementById('url').textContent=s.url||'http://partida-frio.local/';
    wifiLoaded=true;
  }catch(e){}
}
async function saveWifi(){
  const a=document.getElementById('pw').value;
  const b=document.getElementById('pw2').value;
  if(a.length<8||a.length>63){msg('msgWifi','A senha precisa ter de 8 a 63 caracteres.');return}
  if(a!==b){msg('msgWifi','As senhas nao conferem.');return}
  const r=await j('/api/wifi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:a})});
  if(r.ok){
    msg('msgWifi','Senha salva. Conecte de novo no Wi-Fi.');
    document.getElementById('pw').value='';
    document.getElementById('pw2').value='';
    document.getElementById('pwNow').textContent=a;
    closeKb();
  }else{
    msg('msgWifi',r.error||'Nao foi possivel salvar.');
  }
}
document.getElementById('enabled').onchange=live;
document.querySelectorAll('input[name=trig]').forEach(x=>x.onchange=()=>{hint(trig());live()});
['delay_ms','inject_ms','pwm_percent'].forEach(id=>{
  const el=document.getElementById(id);
  el.addEventListener('input',()=>{vals();clearTimeout(saveT);saveT=setTimeout(live,80)});
});
document.querySelectorAll('.kb-box').forEach(box=>{
  box.addEventListener('pointerup', function(e){
    e.stopPropagation();
    openKb(box.querySelector('input.kb'));
  });
});
document.querySelectorAll('input.kb').forEach(el=>{
  el.addEventListener('focus', function(){
    if(kbOpen!==el){
      el.blur();
      el.setAttribute('readonly','readonly');
      el.disabled=true;
      el.tabIndex=-1;
    }
  });
  el.addEventListener('keydown', e=>{
    if(e.key==='Enter'){ e.preventDefault(); closeKb(); }
  });
});
document.addEventListener('pointerdown', function(e){
  if(!kbOpen) return;
  if(e.target===kbOpen || (kbOpen.closest('.kb-box') && kbOpen.closest('.kb-box').contains(e.target))) return;
  closeKb();
}, true);
hint('start');
setInterval(refresh,400);
refresh();
</script>
</body>
</html>
"""


def _wlan_ap():
    if hasattr(network, "WLAN") and hasattr(network.WLAN, "IF_AP"):
        return network.WLAN(network.WLAN.IF_AP)
    return network.WLAN(network.AP_IF)


def _ip_bytes(ip):
    parts = ip.split(".")
    if len(parts) != 4:
        return b"\xc0\xa8\x04\x01"
    try:
        return bytes(int(p) for p in parts)
    except ValueError:
        return b"\xc0\xa8\x04\x01"


def _skip_dns_name(buf, i):
    n = len(buf)
    while i < n:
        lab = buf[i]
        if lab == 0:
            return i + 1
        if lab & 0xC0 == 0xC0:
            return i + 2
        i += 1 + lab
    return i


def _dns_reply(req, ip_bytes):
    if len(req) < 12:
        return None
    i = _skip_dns_name(req, 12)
    if i + 4 > len(req):
        return None
    qtype = (req[i] << 8) | req[i + 1]
    qend = i + 4
    out = bytearray()
    out += req[0:2]
    out += b"\x81\x80"
    out += req[4:6]
    if qtype == 1:
        out += req[4:6]
    else:
        out += b"\x00\x00"
    out += b"\x00\x00\x00\x00"
    out += req[12:qend]
    if qtype == 1:
        out += b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x1e\x00\x04"
        out += ip_bytes
    return bytes(out)


def _start_mdns(hostname):
    try:
        network.hostname(hostname)
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    try:
        import mdns

        if hasattr(mdns, "Server"):
            srv = mdns.Server()
            if hasattr(srv, "hostname"):
                srv.hostname(hostname)
            if hasattr(srv, "start"):
                srv.start()
            return
        if hasattr(mdns, "start"):
            mdns.start(hostname)
    except (ImportError, AttributeError, OSError, TypeError, ValueError):
        pass


class WebServer:
    def __init__(self, controller, cfg):
        self.ctl = controller
        self.cfg = cfg
        self._poll = uselect.poll()
        self._listen = None
        self._dns = None
        self._ssid = AP_SSID
        self._ip = "192.168.4.1"
        self._ip_bytes = b"\xc0\xa8\x04\x01"

    def start(self):
        wlan = _wlan_ap()
        wlan.active(False)
        wlan.active(True)
        self._ssid = AP_SSID
        try:
            wlan.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
        except OSError:
            pass
        self._apply_ap(wlan, restart=False)
        try:
            self._ip = wlan.ifconfig()[0]
        except OSError:
            self._ip = "192.168.4.1"
        self._ip_bytes = _ip_bytes(self._ip)
        _start_mdns(MDNS_HOST)
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 80))
        sock.listen(4)
        sock.settimeout(0)
        self._listen = sock
        self._poll.register(sock, uselect.POLLIN)
        self._start_dns()
        print("wifi AP %s senha %s" % (self._ssid, self.cfg.wifi_password))
        print("http://%s/" % self._ip)
        print("http://%s.local/" % MDNS_HOST)

    def _apply_ap(self, wlan=None, restart=False):
        if wlan is None:
            wlan = _wlan_ap()
        if restart:
            try:
                wlan.active(False)
            except OSError:
                pass
            wlan.active(True)
            try:
                wlan.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
            except OSError:
                pass
        pw = self.cfg.wifi_password
        auth = getattr(network, "AUTH_WPA_WPA2_PSK", None)
        if auth is None:
            auth = getattr(network, "AUTH_WPA2_PSK", 3)
        for kwargs in (
            {"essid": AP_SSID, "password": pw, "authmode": auth},
            {"ssid": AP_SSID, "password": pw, "authmode": auth},
            {"essid": AP_SSID, "password": pw, "security": auth},
            {"ssid": AP_SSID, "password": pw, "security": auth},
            {"essid": AP_SSID, "password": pw},
        ):
            try:
                wlan.config(**kwargs)
                return True
            except (OSError, TypeError, ValueError):
                continue
        try:
            wlan.config(essid=AP_SSID)
        except OSError:
            pass
        return False

    def _start_dns(self):
        try:
            dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            dns.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            dns.bind(("0.0.0.0", 53))
            dns.settimeout(0)
            self._dns = dns
            self._poll.register(dns, uselect.POLLIN)
        except OSError:
            self._dns = None

    def _handle_dns(self):
        if not self._dns:
            return
        try:
            data, addr = self._dns.recvfrom(512)
        except OSError:
            return
        reply = _dns_reply(data, self._ip_bytes)
        if not reply:
            return
        try:
            self._dns.sendto(reply, addr)
        except OSError:
            pass

    def poll(self):
        if not self._listen:
            return
        try:
            ev = self._poll.poll(HTTP_TIMEOUT_MS)
        except OSError:
            return
        if not ev:
            return
        for sock, _flag in ev:
            if self._dns is not None and sock is self._dns:
                self._handle_dns()
            elif sock is self._listen:
                self._accept_http()

    def _accept_http(self):
        try:
            cl, addr = self._listen.accept()
        except OSError:
            return
        try:
            cl.settimeout(1)
            req = b""
            while b"\r\n\r\n" not in req and len(req) < 2048:
                chunk = cl.recv(256)
                if not chunk:
                    break
                req += chunk
            if b"\r\n\r\n" in req:
                header, rest = req.split(b"\r\n\r\n", 1)
                clen = 0
                for line in header.split(b"\r\n"):
                    if line.lower().startswith(b"content-length:"):
                        try:
                            clen = int(line.split(b":", 1)[1].strip())
                        except ValueError:
                            clen = 0
                while len(rest) < clen and len(rest) < 2048:
                    chunk = cl.recv(256)
                    if not chunk:
                        break
                    rest += chunk
                req = header + b"\r\n\r\n" + rest
            self._handle(cl, req)
        except OSError:
            pass
        try:
            cl.close()
        except OSError:
            pass

    def _send_html(self, cl, body):
        if isinstance(body, str):
            body = body.encode()
        cl.send(
            b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
            % len(body)
        )
        cl.send(body)

    def _redirect_home(self, cl):
        loc = ("http://%s/" % self._ip).encode()
        cl.send(
            b"HTTP/1.0 302 Found\r\nLocation: %s\r\nCache-Control: no-store\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            % loc
        )

    def _wifi_info(self):
        return {
            "ssid": AP_SSID,
            "password": self.cfg.wifi_password,
            "ip": self._ip,
            "url": "http://%s.local/" % MDNS_HOST,
        }

    def _handle(self, cl, req):
        try:
            head = req.split(b"\r\n", 1)[0].decode()
            parts = head.split(" ")
            method = parts[0]
            path = parts[1].split("?")[0]
        except (IndexError, UnicodeError):
            cl.send(b"HTTP/1.0 400 Bad Request\r\n\r\n")
            return
        if method == "GET" and path in ("/", "/menu", "/presets", "/settings"):
            self._send_html(cl, INDEX_HTML)
            return
        if method == "GET" and path == "/api/status":
            self._json(cl, self.ctl.status())
            return
        if method == "GET" and path == "/api/wifi":
            self._json(cl, self._wifi_info())
            return
        if method == "POST" and path == "/api/wifi":
            data = self._body_json(req)
            pw = data.get("password", "")
            if not wifi_password_ok(pw):
                self._json(cl, {"ok": False, "error": "Senha invalida. Use 8 a 63 caracteres."})
                return
            if not self.cfg.set_wifi_password(pw):
                self._json(cl, {"ok": False, "error": "Senha invalida. Use 8 a 63 caracteres."})
                return
            self._apply_ap(restart=True)
            out = self._wifi_info()
            out["ok"] = True
            self._json(cl, out)
            return
        if method == "POST" and path == "/api/live":
            data = self._body_json(req)
            if data:
                self.cfg.update(data, persist=False)
            self._json(cl, self.cfg.as_dict())
            return
        if method == "POST" and path == "/api/config":
            data = self._body_json(req)
            if data:
                self.cfg.update(data, persist=True)
            self._json(cl, self.cfg.as_dict())
            return
        if method == "GET" and path == "/api/presets":
            self._json(cl, {"items": self.cfg.list_presets()})
            return
        if method == "POST" and path == "/api/presets":
            data = self._body_json(req)
            items = self.cfg.save_preset(data.get("name", ""))
            self._json(cl, {"items": items})
            return
        if method == "POST" and path == "/api/presets/load":
            data = self._body_json(req)
            ok = self.cfg.load_preset(data.get("name", ""))
            out = self.cfg.as_dict()
            out["ok"] = ok
            self._json(cl, out)
            return
        if method == "POST" and path == "/api/presets/delete":
            data = self._body_json(req)
            items = self.cfg.delete_preset(data.get("name", ""))
            self._json(cl, {"items": items})
            return
        if method == "POST" and path == "/api/test":
            self.ctl.request_start()
            self._json(cl, {"ok": True})
            return
        if method == "GET":
            self._redirect_home(cl)
            return
        cl.send(b"HTTP/1.0 404 Not Found\r\n\r\n")

    def _body_json(self, req):
        try:
            raw = req.split(b"\r\n\r\n", 1)[1]
            if not raw:
                return {}
            return ujson.loads(raw.decode())
        except (IndexError, ValueError, UnicodeError):
            return {}

    def _json(self, cl, obj):
        body = ujson.dumps(obj).encode()
        cl.send(
            b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
            % len(body)
        )
        cl.send(body)
