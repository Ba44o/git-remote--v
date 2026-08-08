// Vira a página da tabela de CRIATIVOS.
// GOTCHA: a página tem DUAS paginações. A primeira (.core-pagination size-default)
// controla a tabela de CAMPANHAS (inútil). A dos criativos é a ".core-pagination-size-mini".
// Clicar na errada muda o estado visual mas não troca os criativos.
(function(){
  function fire(el){ ['mousedown','mouseup','click'].forEach(function(type){
    el.dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true,view:window})); }); }
  function txt(el){ return el ? (el.innerText||el.textContent||'').replace(/\s+/g,' ').trim() : ''; }
  var res = {found:false, how:''};
  var mini = document.querySelector('.core-pagination-size-mini');
  if(mini){
    var nx = mini.querySelector('.core-pagination-item-next');
    if(nx){ fire(nx); res.found=true; res.how='mini-next'; return JSON.stringify(res); }
    var items = mini.querySelectorAll('.core-pagination-item');
    for(var i=0;i<items.length;i++){ if(txt(items[i])==='2'){ fire(items[i]); res.found=true; res.how='mini-2'; return JSON.stringify(res); } }
  }
  return JSON.stringify(res);
})();
