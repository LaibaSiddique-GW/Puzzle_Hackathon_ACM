// Fire background sound for level 3
const fireSound = new Audio('SFX_Loop_Fire.ogg');
fireSound.loop = true;
fireSound.volume = 0.25;

function playFireSound() {
  fireSound.currentTime = 0;
  fireSound.play();
}

function stopFireSound() {
  fireSound.pause();
  fireSound.currentTime = 0;
}
const winSound = new Audio('SFX_Game_Success.ogg');
winSound.volume = 0.4;

function playWinSound() {
  winSound.currentTime = 0;
  winSound.play();
  // Let the sound play fully (2s), do not pause/stop early
  // If you want to ensure it never overlaps, you can pause first:
  // winSound.pause(); winSound.currentTime = 0; winSound.play();
}
const soloSound = new Audio('SFX_UI_Click_1.ogg');
const duoSound = new Audio('SFX_UI_Click_1.ogg');

soloSound.volume = 0.25;
duoSound.volume = 0.25;

function playSoloSound() {
  soloSound.currentTime = 0;
  soloSound.play();
  setTimeout(() => {
    soloSound.pause();
    soloSound.currentTime = 0;
  }, 1000);
}

function playDuoSound() {
  duoSound.currentTime = 0;
  duoSound.play();
  setTimeout(() => {
    duoSound.pause();
    duoSound.currentTime = 0;
  }, 1000);
}
