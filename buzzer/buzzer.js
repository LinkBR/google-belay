// Copyright 2011 Google Inc. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

(function() {
  belay.startForLaunch('client_preimg', function(capServer, util, launchInfo) {
    capServer.setSyncNotifier(function(state) {
      if (launchInfo.snapshot_cap) {
        launchInfo.snapshot_cap.put(state);
      }
    });

    var formAjax = function(form, callback) {
      var data = {};
      for (var i = 0; i < form.elements.length; ++i) {
        var input = form.elements[i];
        if (input.type == 'text' || input.type == 'textarea') {
          data[input.name] = input.value;
        }
        else if (input.type == 'submit') {
          // do nothing
        }
        else {
          alert('Unhandled type of form input: ' +
                   input.type + ' named ' + input.name);
        }
      }
      capServer.restore(form.action).invoke(
        form.method.toUpperCase() || 'GET',
        data,
        callback,
        function(error) {
          alert('form update failed: ' + error.message +
              ' (' + error.status + ')');
        });
    };

    var rcPost = 'urn:x-belay://resource-class/social-feed/postable';
    var rcBelayGen = 'belay/generate';

    capServer.setNamedHandler(rcPost, function() {
      return function(data) {
        launchInfo.post_cap.post(
          {
            body: data.body,
            via: data.via
          },
          reload
        );
      };    
    });

    var reload = function() {
      var buzzerContent = $('#buzzer-content');

      buzzerContent.load(launchInfo.editor_cap.serialize(), function() {
        var forms = buzzerContent.find('.buzzer-thing form');
        buzzerContent.find('.buzzer-thing form').submit(function(ev) {
          formAjax(ev.target, reload);
          ev.preventDefault();
          return false;
        });
        ui.capDraggable(buzzerContent.find('.buzzer-reader-chit'), rcBelayGen,
            launchInfo.reader_gen_cap,
            launchInfo.readChitURL);
        ui.capDraggable(buzzerContent.find('.buzzer-post-chit'), rcPost,
            capServer.grant(function(selectedRC) {
                return {
                  post: capServer.grantNamed(selectedRC),
                  name: capServer.grant(function() {
                      return $('#buzzer-name').text().trim();
                    })
                };
            }),
            launchInfo.postChitURL);
        window.belaytest.ready = true;
      });
    };

    $(reload);

    util.setRefresh.put(capServer.grant(reload));
  });
})();
