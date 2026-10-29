/* Static translated bodies are already complete before JavaScript runs. */
(function(){
  'use strict';
  var config=document.getElementById('marketing-config'), ui=document.getElementById('marketing-ui-data');
  try{window.MSRA=JSON.parse(config.textContent);window.MSRA.staticDictionary=JSON.parse(ui.textContent);}catch(error){return;}
})();
