'use strict';
const $ = (id) => document.getElementById(id);
const activities = {
  idle: '느긋하게 쉬는 중', focus: '생각하는 중', working: '열심히 작업하는 중',
  waiting: '네 확인을 기다리는 중', complete: '별이 반짝이는 중',
  interrupted: '잠시 멈춘 중', sleepy: '꿈꾸며 쉬는 중'
};
const render = (s) => {
  $('connection-label').textContent = '별정원 연결됨';
  $('name').textContent = s.name;
  $('level').textContent = 'LV. ' + s.level;
  $('form').textContent = s.form;
  $('speech').textContent = s.message;
  $('scenery').dataset.mood = s.activity;
  $('activity-label').textContent = activities[s.activity] || activities.idle;
  $('xp-label').textContent = `${s.xp} / ${s.next_level_xp} XP`;
  $('xp-fill').style.width = `${s.level_progress}%`;
  $('xp-track').setAttribute('aria-valuenow', s.level_progress);
  $('bond').textContent = s.bond;
  $('energy').textContent = s.energy;
  $('bond-fill').style.width = `${s.bond}%`;
  $('energy-fill').style.width = `${s.energy}%`;
  $('turns').textContent = s.turns;
  $('stardust').textContent = `${s.stardust} ✦`;
  $('streak').textContent = s.streak + '일';
  $('footer-version').textContent = 'ARI v' + s.version;
};
async function refresh() {
  try {
    const response = await fetch('/api/status', {cache:'no-store'});
    if (!response.ok) throw new Error('Unavailable');
    render(await response.json());
  } catch (err) {
    $('connection-label').textContent = '연결을 확인해 줘';
  }
}
let busy = false;
async function act(action) {
  if (busy) return;
  busy = true;
  const buttons = document.querySelectorAll('.action');
  buttons.forEach(b => b.disabled = true);
  try {
    const response = await fetch('/api/action', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'X-Ari-Pet':'1'},
      body: JSON.stringify({action})
    });
    if (!response.ok) throw new Error('Action unavailable');
    render(await response.json());
  } catch (err) {
    $('connection-label').textContent = '잠시 연결이 끊겼어';
  } finally {
    busy = false;
    buttons.forEach(b => b.disabled = false);
  }
}
document.querySelectorAll('.action').forEach(button => {
  button.addEventListener('click', () => act(button.dataset.action));
});
document.addEventListener('keydown', event => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.repeat) return;
  const mapping = {'1':'pet','2':'feed','3':'play','4':'rest'};
  if (mapping[event.key] && !['INPUT','TEXTAREA'].includes(document.activeElement?.tagName)) act(mapping[event.key]);
});
refresh();
setInterval(refresh, 1500);
