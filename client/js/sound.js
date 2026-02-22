const soloSound = new Audio('solo_sound.mp3');
const duoSound = new Audio('duo_sound.mp3');

soloSound.volume = 0.25;
duoSound.volume = 0.25;

function playSoloSound() {
  soloSound.currentTime = 0;
  soloSound.play();
  setTimeout(() => {
    soloSound.pause();
    soloSound.currentTime = 0;
  }, 10000);
}

function playDuoSound() {
  duoSound.currentTime = 0;
  duoSound.play();
  setTimeout(() => {
    duoSound.pause();
    duoSound.currentTime = 0;
  }, 10000);
}
