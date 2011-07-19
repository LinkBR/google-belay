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

$(function() {
  var topDiv = $(document.body).find('.buzzer-thing');
  var form = topDiv.find('#profileForm');
  form.submit(function(evt) {
    var name = form.find('[name="name"]').val();
    var loc = form.find('[name="location"]').val();

    $.ajax({
      url: '/belay/generateProfile',
      dataType: 'text',
      type: 'POST',
      data: {name: name, location: loc},
      success: function(data, status, xhr) {
        var instanceName = name + " from " +  loc;
        console.log(instanceName);
        console.log(data);

        belayPort.postMessage({
          type: 'instanceRequest',
          gen: JSON.stringify({value: {
            launch: JSON.parse(data).value,
            icon: 'http://localhost:9004/tool-buzzer.png',
            name: instanceName
          }})
        });
      },
      failure: function() {
        console.log('JSON failed');
      }
    });
    evt.preventDefault();
    return false;
  });
});