/** @odoo-module **/

// ===== Util =====
function onReady(fn) { if (document.readyState !== "loading") fn(); else document.addEventListener("DOMContentLoaded", fn); }
function escapeHtml(s){return String(s||"").replace(/[&<>"']/g,(c)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function fmtPrice(v){const n=Number(v||0);const sym=document.querySelector(".oe_currency_symbol")?.textContent?.trim()||"";return `${sym?sym+" ":""}${n.toFixed(2)}`;}

// ===== Atributos =====
function sortSizes(opts){
  const std=["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
  return [...opts].sort((a,b)=>{
    const na=parseFloat(a.text), nb=parseFloat(b.text);
    if(!isNaN(na)&&!isNaN(nb)) return na-nb;
    const ia=std.indexOf(a.text.toUpperCase()), ib=std.indexOf(b.text.toUpperCase());
    if(ia>=0&&ib>=0) return ia-ib;
    return a.text.localeCompare(b.text, undefined, {numeric:true});
  });
}

function getAttributeBlocks(scope){
  const blocks=[];
  const containers=Array.from(scope.querySelectorAll('.js_product .js_attributes > div, .js_attribute, [data-attribute_name]'));
  containers.forEach((el)=>{
    const name=(el.getAttribute("data-attribute_name")||el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent||el.getAttribute("name")||"").trim().toLowerCase();
    const radios=Array.from(el.querySelectorAll('input[type="radio"]'));
    if(!radios.length) return;
    const options=radios.map((inp)=>{
      const pav=parseInt(inp.dataset.attributeValueId || inp.getAttribute('data-attribute_value_id') || "0",10)||0; // Product Attribute Value
      const ptav=parseInt(inp.dataset.valueId || inp.getAttribute('data-value-id') || "0",10)||0; // Product Template Attribute Value
      const txt=(inp.closest("label")?.textContent || inp.getAttribute("title") || "").replace(/\s+/g," ").trim();
      return (pav||ptav)? {pav, ptav, text: txt} : null;
    }).filter(Boolean);
    if(options.length) blocks.push({name, options});
  });

  const color=blocks.find(b=>/(color|colour|colou?r|c[oó]lor)/i.test(b.name));
  const size =blocks.find(b=>/(size|talla|talle|taille|größe|maat)/i.test(b.name));
  if(size) size.options=sortSizes(size.options);
  return {color,size};
}

// ===== API =====
async function fetchCombos(templateId){
  const r=await fetch(`/sp/matrix/combos/${templateId}`,{
    method:"POST", headers:{"Content-Type":"application/json","X-Requested-With":"XMLHttpRequest"},
    body:JSON.stringify({}), credentials:"same-origin"
  });
  return r.json();
}
async function addBatch(lines){
  const r=await fetch("/sp/cart/add_batch",{
    method:"POST", headers:{"Content-Type":"application/json","X-Requested-With":"XMLHttpRequest"},
    body:JSON.stringify({lines}), credentials:"same-origin"
  });
  return r.json();
}

// ===== Render =====
function buildGridHTML(color,size){
  const hasSize=!!size;
  const cols=hasSize? size.options : [{pav:0,ptav:0,text:"One Size"}];

  let thead='<thead><tr><th class="sp-sticky-left">Color</th>';
  cols.forEach(s=> thead+=`<th>${escapeHtml(s.text)}</th>`);
  thead+='</tr></thead>';

  let tbody='<tbody>';
  color.options.forEach(c=>{
    tbody+=`<tr data-color-ptav="${c.ptav||""}" data-color-pav="${c.pav||""}">
      <th class="sp-sticky-left">
        <div class="sp-color">
          <img class="sp-color__img" alt="">
          <span>${escapeHtml(c.text)}</span>
        </div>
      </th>`;
    cols.forEach(s=>{
      tbody+=`<td>
        <div class="sp-cell" data-size-ptav="${s.ptav||""}" data-size-pav="${s.pav||""}">
          <input class="sp-qty" type="number" min="0" step="1" inputmode="numeric" placeholder="0">
          <div class="sp-meta"></div>
        </div>
      </td>`;
    });
    tbody+='</tr>';
  });
  tbody+='</tbody>';

  return `<div id="sp-matrix" class="sp-matrix-box">
    <table class="sp-matrix__table">${thead}${tbody}</table>
    <div class="sp-actions"><button type="button" class="btn btn-primary sp-add">Añadir selección</button></div>
    <p class="sp-help">Indica cantidades por color y talla.</p>
  </div>`;
}

// ==== [MEJORA] Obtener template id de más sitios ====
function getTemplateId(page){
  const inp=page.querySelector('input[name="product_template_id"]');
  if(inp) return parseInt(inp.value,10);
  const self = page.getAttribute("data-product-template-id"); // algunos themes lo ponen aquí
  if(self) return parseInt(self,10);
  const any = page.querySelector('[data-product-template-id]'); // p.ej. #product_details
  if(any) return parseInt(any.getAttribute('data-product-template-id'),10);
  return null;
}

function findInsertPoint(page){
  const attrs=page.querySelector(".js_product .js_attributes");
  if(!attrs) return null;                     // Solo pintamos si existen atributos (evita que salga abajo)
  return {el: attrs, where: "afterend"};      // Inmediatamente debajo de los atributos
}

function removeOldGrid(page){ page.querySelectorAll("#sp-matrix").forEach(n=>n.remove()); }

async function ensureMatrix(){
  const page=document.querySelector(".o_wsale_product_page");
  if(!page) return;

  const {color,size}=getAttributeBlocks(page);
  const pos=findInsertPoint(page);
  if(!color || !pos){ removeOldGrid(page); return; }

  removeOldGrid(page);
  pos.el.insertAdjacentHTML(pos.where, buildGridHTML(color,size));

  const matrix=page.querySelector("#sp-matrix");
  const templateId=getTemplateId(page);
  if(!templateId) return;

  // Datos del servidor
  let combos={};
  try{ combos=await fetchCombos(templateId);}catch(e){ combos={ok:false}; }
  const items = combos.ok ? (combos.items||[]) : [];

  // Imagen por color (match por PTAV o PAV)
  matrix.querySelectorAll("tr[data-color-pav]").forEach(tr=>{
    const cPTAV=parseInt(tr.dataset.colorPtav||"0",10);
    const cPAV =parseInt(tr.dataset.colorPav ||"0",10);
    const img=tr.querySelector(".sp-color__img");
    const hit=items.find(it => cPTAV ? it.ptav_ids.includes(cPTAV) : (cPAV ? it.pav_ids.includes(cPAV) : false));
    img.src = (hit && hit.image) ? hit.image : "/web/static/img/placeholder.png";
  });

  // Info por celda y product_id
  matrix.querySelectorAll(".sp-cell").forEach(cell=>{
    const tr=cell.closest("tr");
    const cPTAV=parseInt(tr.dataset.colorPtav||"0",10);
    const cPAV =parseInt(tr.dataset.colorPav ||"0",10);
    const sPTAV=parseInt(cell.dataset.sizePtav||"0",10);
    const sPAV =parseInt(cell.dataset.sizePav ||"0",10);

    const prod=items.find(it=>{
      const hitColor = cPTAV ? it.ptav_ids.includes(cPTAV) : (cPAV ? it.pav_ids.includes(cPAV) : false);
      const hitSize  = (sPTAV||sPAV) ? (sPTAV ? it.ptav_ids.includes(sPTAV) : it.pav_ids.includes(sPAV)) : true;
      return hitColor && hitSize;
    });

    if(prod){
      cell.dataset.productId=String(prod.product_id);
      cell.querySelector(".sp-meta").textContent=`${fmtPrice(prod.price)} · stock ${prod.stock}`;
      cell.classList.remove("sp-unavailable");
      cell.querySelector(".sp-qty").disabled=false;
    }else{
      cell.dataset.productId="";
      cell.querySelector(".sp-meta").textContent="—";
      cell.classList.add("sp-unavailable");
      cell.querySelector(".sp-qty").disabled=true;
    }
  });

  // Añadir selección (batch)
  matrix.querySelector(".sp-add")?.addEventListener("click", async (ev)=>{
    const btn=ev.currentTarget;
    const lines=[];
    matrix.querySelectorAll(".sp-cell").forEach(cell=>{
      const pid=parseInt(cell.dataset.productId||"0",10);
      const qty=parseFloat(cell.querySelector(".sp-qty")?.value||"0");
      if(pid && qty>0) lines.push({product_id:pid, qty});
    });
    if(!lines.length){ btn.classList.add("shake"); setTimeout(()=>btn.classList.remove("shake"),500); return; }
    btn.disabled=true; btn.textContent="Añadiendo…";
    try{
      const res=await addBatch(lines);
      if(!res.ok) throw new Error("cart error");
      btn.textContent="Añadido ✔";
      document.querySelectorAll(".o_website_sale .my_cart_quantity, .js_cart_qty").forEach(el=>el.dispatchEvent(new Event("change")));
    }catch(e){ btn.textContent="Error"; }
    finally{ setTimeout(()=>{ btn.disabled=false; btn.textContent="Añadir selección"; },1200); }
  });
}

// ===== Arranque y anti-duplicados =====
onReady(()=>{
  const page=document.querySelector(".o_wsale_product_page");
  if(!page) return;

  // 1) Si ya están los atributos, pinto
  let attrs=page.querySelector(".js_product .js_attributes");
  if (attrs) {
    ensureMatrix();
    attrs.addEventListener("change",(ev)=>{ if(ev.target.matches('input[type="radio"]')) ensureMatrix(); });
    const mo=new MutationObserver(()=>ensureMatrix());
    mo.observe(attrs,{childList:true, subtree:true});
  } else {
    // 2) [NUEVO] Esperar a que aparezcan los atributos (evita “grid desaparecido”)
    const wait = new MutationObserver(()=>{
      attrs = page.querySelector(".js_product .js_attributes");
      if (attrs) {
        wait.disconnect();
        ensureMatrix();
        attrs.addEventListener("change",(ev)=>{ if(ev.target.matches('input[type="radio"]')) ensureMatrix(); });
        const mo=new MutationObserver(()=>ensureMatrix());
        mo.observe(attrs,{childList:true, subtree:true});
      }
    });
    wait.observe(page, {childList:true, subtree:true});
  }
});