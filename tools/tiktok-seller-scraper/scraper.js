// Raspa a tabela de criativos do TikTok Seller (relatório de vídeo / GMV Max).
// Serve p/ métricas UI-only que nenhuma API entrega: hook 2s/6s, retenção 25/50/75/100%,
// taxa de conversão do anúncio. Retorna JSON {url, headers[], rows[][]}.
(function(){
  function txt(el){ return (el.innerText||'').replace(/\s+/g,' ').trim(); }
  var tables = Array.prototype.slice.call(document.querySelectorAll('table'));
  var result = { url: location.href, headers: [], rows: [] };
  if (tables.length){
    // Manter só as tabelas do grid principal = as que têm a MAIOR contagem de linhas.
    // A página tem uma tabela de CAMPANHAS sobreposta (menos linhas) que corromperia o merge.
    var counts = tables.map(function(t){ return t.querySelectorAll('tbody tr').length; });
    var maxRows = Math.max.apply(null, counts);
    var grid = tables.filter(function(t,i){ return counts[i] === maxRows; });
    grid.sort(function(a,b){ return a.getBoundingClientRect().left - b.getBoundingClientRect().left; });
    grid.forEach(function(t){
      var ths = t.querySelectorAll('thead th');
      for (var i=0;i<ths.length;i++){ result.headers.push(txt(ths[i])); }
    });
    var perTable = grid.map(function(t){ return Array.prototype.slice.call(t.querySelectorAll('tbody tr')); });
    for (var ri=0; ri<maxRows; ri++){
      var row = [];
      perTable.forEach(function(rows){
        var tr = rows[ri];
        if (tr){
          var tds = tr.querySelectorAll('td');
          for (var ci=0; ci<tds.length; ci++){ row.push(txt(tds[ci])); }
        }
      });
      if (row.join('').length) result.rows.push(row);
    }
  }
  if (!result.rows.length){
    var rrows = document.querySelectorAll('[role=row]');
    for (var k=0;k<rrows.length;k++){
      var cells = rrows[k].querySelectorAll('[role=cell],[role=columnheader],[role=gridcell]');
      var arr=[]; for (var m=0;m<cells.length;m++){ arr.push(txt(cells[m])); }
      if (arr.join('').length) result.rows.push(arr);
    }
  }
  return JSON.stringify(result);
})();
