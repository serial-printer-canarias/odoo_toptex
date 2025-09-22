/** @odoo-module **/

// === Utilidad que te funcionaba ===
function onReady(fn){ if(document.readyState!=="loading") fn(); else document.addEventListener("DOMContentLoaded", fn); }
function escapeHtml(s){return String(s||"").replace(/[&<>"']/g,(c)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function fmtPrice(v){const n=Number(v||0);const sym=document.querySelector(".oe_currency_symbol")?.textContent?.trim()||"";return `${sym?sym+" ":""}${n.toFixed(2)}`;}

// === Orden tallas ===
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

// === Leer bloques de atributos ===
function getAttributeBlocks(scope){
  const blocks=[];
  const containers=Array.from(scope.querySelectorAll('.js_product .js_attributes > div, .js_attribute, [data-attribute_name]'));
  containers.forEach((el)=>{
    const name=(el.getAttribute("data-attribute_name")||el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent||el.getAttribute("name")||"").trim().toLowerCase();
    const radios=Array.from(el.querySelectorAll('input[type="radio"]'));
    if(!radios.length) return;
    const options=radios.map((inp)=>{
      const pav=parseInt(inp.dataset.attributeValueId || inp.getAttribute('data-attribute_value_id') || "0",10)||0;
      const ptav=parseInt(inp.dataset.valueId || inp.getAttribute('data-value-id') || "0",10)||0;
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

// === API ===
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

// === Utilidades de página ===
function getTemplateId(page){
  const inp=page.querySelector('input[name="product_template_id"]');
  if(inp) return parseInt(inp.value,10);
  const self=page.getAttribute("data-product-template-id");
  if(self) return parseInt(self,10);
  const any=page.querySelector('[data-product-template-id]');
  if(any) return parseInt(any.getAttribute('data-product-template-id'),10);
  return null;
}
function anchorAfterAttributes(page){
  const attrs=page.querySelector(".js_product .js_attributes");
  return attrs ? {el: attrs, where: "afterend"} : null;
}
function removeOldGrid(page){ page.querySelectorAll("#sp-matrix").forEach(n=>n.remove()); }

// === Render ===
function renderGrid(color,size){
  const cols = size ? size.options : [{pav:0, ptav:0, text:"One Size"}];
  let thead='<thead><tr><th class="sp-sticky-left">Color</th>';
  cols.forEach(s=> thead+=`<th>${escapeHtml(s.text)}</th>`); thead+='</tr></thead>';
  let tbody='<tbody>';
  color.options.forEach(c=>{
    tbody+=`<tr data-color-ptav="${c.ptav||""}" data-color-pav="${c.pav||""}">
      <th class="sp-sticky-left">
        <div class="sp-color"><img class="sp-color__img" alt=""><span>${escapeHtml(c.text)}</span></div>
      </th>`;
    cols.forEach(s=>{
      tbody+=`<td><div class="sp-cell" data-size-ptav="${s.ptav||""}" data-size-pav="${s.pav||""}">
        <input class="sp-qty" type="number" min="0" step="1" inputmode="numeric" placeholder="0">
        <div class="sp-meta"></div></div></td>`;
    });
    tbody+='</tr>';
  });
  tbody+='</tbody>';
  return `<div id="sp-matrix"><table class="sp-matrix__table">${thead}${tbody}</table>
    <div class="sp-actions"><button type="button" class="btn btn-primary sp-add">Añadir selección</button></div>
    <p class="sp-help">Indica cantidades por color y talla.</p></div>`;
}

async function ensureMatrix(){
  const page=document.querySelector(".o_wsale_product_page");
  if(!page) return;

  const pos=anchorAfterAttributes(page);
  const {color,size}=getAttributeBlocks(page);
  if(!pos || !color){ removeOldGrid(page); return; }

  removeOldGrid(page);
  pos.el.insertAdjacentHTML(pos.where, renderGrid(color,size));

  const matrix=page.querySelector("#sp-matrix");
  const templateId=getTemplateId(page);
  if(!templateId) return;

  let combos={ok:false, items:[]};
  try{ combos=await fetchCombos(templateId); }catch(e){}
  const items = combos.ok ? combos.items : [];

  // miniaturas por color
  matrix.querySelectorAll("tr[data-color-pav]").forEach(tr=>{
    const cPTAV=parseInt(tr.dataset.colorPtav||"0",10);
    const cPAV =parseInt(tr.dataset.colorPav ||"0",10);
    const img=tr.querySelector(".sp-color__img");
    const hit=items.find(it => cPTAV ? it.ptav_ids.includes(cPTAV) : (cPAV ? it.pav_ids.includes(cPAV) : false));
    img.src = (hit && hit.image) ? hit.image : "/web/static/img/placeholder.png";
  });

  // meta por celda + product_id
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

  matrix.querySelector(".sp-add")?.addEventListener("click", async (ev)=>{
    const btn=ev.currentTarget;
    const lines=[];
    matrix.querySelectorAll(".sp-cell").forEach(cell=>{
      const pid=parseInt(cell.dataset.productId||"0",10);
      const qty=parseFloat(cell.querySelector(".sp-qty")?.value||"0");
      if(pid && qty>0) lines.push({product_id:pid, qty});
    });
    if(!lines.length){ btn.classList.add("disabled"); setTimeout(()=>btn.classList.remove("disabled"),400); return; }
    btn.disabled=true; btn.textContent="Añadiendo…";
    try{ const res=await addBatch(lines); if(!res.ok) throw 0; btn.textContent="Añadido ✔"; }
    catch(e){ btn.textContent="Error"; }
    finally{ setTimeout(()=>{ btn.disabled=false; btn.textContent="Añadir selección"; },1200); }
  });
}

// Arranque controlado y trazas
onReady(()=>{
  console.info("[SP] product_matrix.js cargado");
  const page=document.querySelector(".o_wsale_product_page");
  if(!page) return;
  const paint=()=>ensureMatrix();
  if(page.querySelector(".js_product .js_attributes")) paint();
  page.addEventListener("change",(ev)=>{
    if(ev.target.matches('.js_product .js_attributes input[type="radio"]')) paint();
  });
  const mo=new MutationObserver((muts)=>{
    for(const m of muts){
      if(m.type==="childList" && (m.target.closest?.(".js_product .js_attributes") || m.target.matches?.(".js_product .js_attributes"))){ paint(); break; }
    }
  });
  mo.observe(page,{childList:true,subtree:true});
  // helper de diagnóstico en consola
  window.spMatrixPing = paint;
});