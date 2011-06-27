var instance;
var tunnel;
var capServer = new os.CapServer();

var resolver = function(instID) {
  if(!instance || !instance.capServer) {
    return tunnel.sendInterface;
  }
  if(instID === instance.capServer.instanceID) {
    return instance.capServer.publicInterface;
  }
  return tunnel.sendInterface;
}

capServer.setResolver(resolver);

tunnel = new os.CapTunnel(os.window.opener);
tunnel.setLocalResolver(resolver);

function waitOnOutpost(tunnel, success, failure) {
  var onReady = function() { 
    if(tunnel.outpost) { 
      os.clearInterval(intervalID);
      os.clearTimeout(timerID);
      success(tunnel);
    }
  }; 
  var intervalID = os.setInterval(onReady, 100);

  var timerID = os.setTimeout(function() { 
    os.clearInterval(intervalID); 
    failure();
  }, 3000);
}


var setupCapServer = function(inst) {
  var instServer;
  if ('capSnapshot' in inst.info) {
    instServer = new os.CapServer(inst.info.capSnapshot);
  }
  else {
    instServer = new os.CapServer();
  }
  inst.capServer = instServer;
  instServer.setResolver(resolver);
};

var setupInstance = function(seedSer) {
  var seedCap = capServer.restore(seedSer);
  seedCap.get(function(instInfo) {
    var inst = {
      icap: seedCap,
      info: instInfo
    };
    setupCapServer(inst);
    inst.id = inst.capServer.instanceID; // TODO(joe): transitive hack!
    instance = inst;
    launchInstance(inst); 
  });
}

waitOnOutpost(tunnel,
    function(tunnel) { setupInstance(tunnel.outpost.seedSer); },
    function() {  } );



os.jQuery.ajax({
  url: 'http://localhost:9001/substation.html',
  dataType: 'text',
  success: function(data, status, xhr) {
    os.topDiv.html(data);
  },
  error: function(xhr, status, error) {
    os.alert('Failed to load station: ' + status);
  }
});


var isDirty = false;
var dirtyProcess = function() {
  if(!instance) { return; }
  inst.info.capSnapshot = inst.capServer.snapshot();
  inst.icap.post(inst.info);
  isDirty = false;
}
var dirty = function() {
  if (isDirty) { return; }
  isDirty = true;
  os.setTimeout(dirtyProcess, 1000);
};

var launchInstance = function(inst) {
  var instInfo = inst.info;
  var top = os.topDiv.find("#substation-container");

  var extras = {
    storage: {
      get: function() { return instInfo.data; },
      put: function(d) { instInfo.data = d; dirty(inst); }
    },
    capServer: inst.capServer,
    ui: {
      resize: function(minWidth, minHeight, isResizable) {
        // Do not think we can make an OS window un-resizable.
        os.topDiv.width(minWidth || '50em')
                 .height(minHeight || '50em');
      },
      capDraggable: function() { /* TODO: implement */ },
      capDroppable: function() { /* TODO: implement */ }
    }
  };

  os.foop(instInfo.iurl, top, extras);
}
