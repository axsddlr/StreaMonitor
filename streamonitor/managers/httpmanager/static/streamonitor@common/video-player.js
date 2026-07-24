(function () {
    'use strict';

    var SVG = {
        play: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',
        pause: '<svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>',
        volumeHigh: '<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>',
        volumeLow: '<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>',
        volumeMute: '<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/><line x1="2" y1="2" x2="22" y2="22" stroke="currentColor" stroke-width="2"/></svg>',
        fullscreen: '<svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>',
        fullscreenExit: '<svg viewBox="0 0 24 24"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/></svg>',
        pip: '<svg viewBox="0 0 24 24"><path d="M19 11h-8v6h8v-6zm4 8V4.98C23 3.88 22.1 3 21 3H3C1.9 3 1 3.88 1 4.98V19c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2zm-2 .02H3V4.97h18v14.05z"/></svg>',
        theater: '<svg viewBox="0 0 24 24"><path d="M18 4h2v4h-2V4zm-2 14v-4h-2v4h2zm4-8h2v4h-2v-4zm-12 4v-4H6v4h2zm4-8h2v4h-2V6zm-4 12v-4H6v4h2zM4 6h2v12H4V6z"/></svg>',
        loop: '<svg viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>',
        prev: '<svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>',
        next: '<svg viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>',
        download: '<svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>',
        check: '<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>'
    };

    var STORAGE_KEY = 'streamonitor_player';
    var IDLE_TIMEOUT = 3000;
    var SEEK_STEP = 5;
    var SEEK_STEP_LARGE = 10;

    function loadSettings() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
        } catch (e) {
            return {};
        }
    }

    function saveSettings(settings) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
        } catch (e) {}
    }

    function formatTime(seconds) {
        if (isNaN(seconds) || !isFinite(seconds)) return '0:00';
        var s = Math.floor(seconds);
        var h = Math.floor(s / 3600);
        var m = Math.floor((s % 3600) / 60);
        var sec = s % 60;
        if (h > 0) {
            return h + ':' + String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
        }
        return m + ':' + String(sec).padStart(2, '0');
    }

    function clamp(val, min, max) {
        return Math.max(min, Math.min(max, val));
    }

    function findVideoList() {
        var list = document.querySelector('#video-list');
        if (!list) return [];
        return list.querySelectorAll('a[href*="/videos/watch/"]');
    }

    function findVideoLinks() {
        var list = document.querySelector('#video-list');
        if (!list) return [];
        return list.querySelectorAll('a[hx-get*="/videos/watch/"]');
    }

    function VideoPlayer(el) {
        if (el._smPlayer) return el._smPlayer;
        el._smPlayer = this;

        this.video = el;
        this.container = null;
        this.built = false;
        this.settings = loadSettings();
        this.idleTimer = null;
        this.isIdle = false;
        this.isScrubbing = false;
        this.volumeBeforeMute = 1;

        this._onTimeUpdate = this._onTimeUpdate.bind(this);
        this._onProgress = this._onProgress.bind(this);
        this._onVolumeChange = this._onVolumeChange.bind(this);
        this._onPlay = this._onPlay.bind(this);
        this._onPause = this._onPause.bind(this);
        this._onEnded = this._onEnded.bind(this);
        this._onWaiting = this._onWaiting.bind(this);
        this._onCanPlay = this._onCanPlay.bind(this);
        this._onFullscreenChange = this._onFullscreenChange.bind(this);

        this.build();
    }

    VideoPlayer.prototype.build = function () {
        var self = this;
        var video = this.video;
        var parent = video.parentNode;

        video.removeAttribute('controls');
        video.setAttribute('playsinline', '');
        video.setAttribute('disablePictureInPicture', '');

        var container = document.createElement('div');
        container.className = 'sm-player';
        container.innerHTML =
            '<div class="sm-player__video-wrapper">' +
                '<div class="sm-player__overlay"></div>' +
                '<div class="sm-player__center-play">' + SVG.play + '</div>' +
                '<div class="sm-player__loading"><div class="sm-player__loading-spinner"></div></div>' +
                '<div class="sm-player__speed-indicator"></div>' +
                '<div class="sm-player__next-overlay">' + SVG.next + '<span>Next video</span></div>' +
            '</div>' +
            '<div class="sm-player__controls">' +
                '<div class="sm-player__progress">' +
                    '<div class="sm-player__progress-track">' +
                        '<div class="sm-player__progress-buffer"></div>' +
                        '<div class="sm-player__progress-fill"></div>' +
                    '</div>' +
                    '<div class="sm-player__progress-thumb"></div>' +
                    '<div class="sm-player__progress-tooltip"></div>' +
                '</div>' +
                '<div class="sm-player__controls-row">' +
                    '<button class="sm-player__btn sm-player__btn--play" title="Play/Pause (Space)">' + SVG.play + '</button>' +
                    '<button class="sm-player__btn sm-player__btn--prev" title="Previous Video (Shift+P)">' + SVG.prev + '</button>' +
                    '<button class="sm-player__btn sm-player__btn--next" title="Next Video (Shift+N)">' + SVG.next + '</button>' +
                    '<div class="sm-player__volume">' +
                        '<button class="sm-player__btn sm-player__btn--mute" title="Mute (M)">' + SVG.volumeHigh + '</button>' +
                        '<div class="sm-player__volume-slider"><input type="range" min="0" max="100" step="1" value="100"></div>' +
                    '</div>' +
                    '<span class="sm-player__time"><span class="sm-player__time-current">0:00</span><span class="sm-player__time-sep"> / </span><span class="sm-player__time-duration">0:00</span></span>' +
                    '<div class="sm-player__spacer"></div>' +
                    '<select class="sm-player__speed" title="Playback Speed (< / >)">' +
                        '<option value="0.25">0.25x</option>' +
                        '<option value="0.5">0.5x</option>' +
                        '<option value="0.75">0.75x</option>' +
                        '<option value="1" selected>1x</option>' +
                        '<option value="1.25">1.25x</option>' +
                        '<option value="1.5">1.5x</option>' +
                        '<option value="2">2x</option>' +
                    '</select>' +
                    '<button class="sm-player__btn sm-player__btn--loop sm-player__btn--toggle" title="Loop (L)">' + SVG.loop + '</button>' +
                    '<button class="sm-player__btn sm-player__btn--pip" title="Picture in Picture">' + SVG.pip + '</button>' +
                    '<button class="sm-player__btn sm-player__btn--theater sm-player__btn--toggle" title="Theater Mode (T)">' + SVG.theater + '</button>' +
                    '<button class="sm-player__btn sm-player__btn--fullscreen" title="Fullscreen (F)">' + SVG.fullscreen + '</button>' +
                '</div>' +
            '</div>';

        var wrapper = container.querySelector('.sm-player__video-wrapper');

        parent.insertBefore(container, video);
        wrapper.insertBefore(video, wrapper.firstChild);

        this.container = container;
        this.built = true;

        this.playBtn = container.querySelector('.sm-player__btn--play');
        this.prevBtn = container.querySelector('.sm-player__btn--prev');
        this.nextBtn = container.querySelector('.sm-player__btn--next');
        this.muteBtn = container.querySelector('.sm-player__btn--mute');
        this.volumeSlider = container.querySelector('.sm-player__volume-slider input');
        this.timeCurrent = container.querySelector('.sm-player__time-current');
        this.timeDuration = container.querySelector('.sm-player__time-duration');
        this.speedSelect = container.querySelector('.sm-player__speed');
        this.loopBtn = container.querySelector('.sm-player__btn--loop');
        this.theaterBtn = container.querySelector('.sm-player__btn--theater');
        this.fullscreenBtn = container.querySelector('.sm-player__btn--fullscreen');
        this.pipBtn = container.querySelector('.sm-player__btn--pip');
        this.progressEl = container.querySelector('.sm-player__progress');
        this.progressFill = container.querySelector('.sm-player__progress-fill');
        this.progressBuffer = container.querySelector('.sm-player__progress-buffer');
        this.progressThumb = container.querySelector('.sm-player__progress-thumb');
        this.progressTooltip = container.querySelector('.sm-player__progress-tooltip');
        this.centerPlay = container.querySelector('.sm-player__center-play');
        this.speedIndicator = container.querySelector('.sm-player__speed-indicator');
        this.nextOverlay = container.querySelector('.sm-player__next-overlay');
        this.overlay = container.querySelector('.sm-player__overlay');

        this.bindEvents();
        this.applySettings();
    };

    VideoPlayer.prototype.bindEvents = function () {
        var self = this;
        var video = this.video;
        var container = this.container;

        video.addEventListener('timeupdate', this._onTimeUpdate);
        video.addEventListener('progress', this._onProgress);
        video.addEventListener('volumechange', this._onVolumeChange);
        video.addEventListener('play', this._onPlay);
        video.addEventListener('pause', this._onPause);
        video.addEventListener('ended', this._onEnded);
        video.addEventListener('waiting', this._onWaiting);
        video.addEventListener('canplay', this._onCanPlay);
        video.addEventListener('loadedmetadata', this._onTimeUpdate);

        this.playBtn.addEventListener('click', function () { self.togglePlay(); });
        this.prevBtn.addEventListener('click', function () { self.prevVideo(); });
        this.nextBtn.addEventListener('click', function () { self.nextVideo(); });
        this.muteBtn.addEventListener('click', function () { self.toggleMute(); });
        this.loopBtn.addEventListener('click', function () { self.toggleLoop(); });
        this.theaterBtn.addEventListener('click', function () { self.toggleTheater(); });
        this.fullscreenBtn.addEventListener('click', function () { self.toggleFullscreen(); });
        this.pipBtn.addEventListener('click', function () { self.togglePiP(); });

        this.speedSelect.addEventListener('change', function () {
            self.setSpeed(parseFloat(self.speedSelect.value));
        });

        this.volumeSlider.addEventListener('input', function () {
            self.setVolume(parseInt(self.volumeSlider.value) / 100);
        });

        this.overlay.addEventListener('click', function () { self.togglePlay(); });
        this.overlay.addEventListener('dblclick', function () { self.toggleFullscreen(); });

        this.centerPlay.addEventListener('click', function (e) {
            e.stopPropagation();
            self.togglePlay();
        });

        container.addEventListener('mousemove', function () { self.showControls(); });
        container.addEventListener('mousedown', function () { self.showControls(); });
        container.addEventListener('touchstart', function () { self.showControls(); });

        document.addEventListener('fullscreenchange', this._onFullscreenChange);
        document.addEventListener('webkitfullscreenchange', this._onFullscreenChange);

        this.progressEl.addEventListener('mousedown', function (e) { self._onScrubStart(e); });
        this.progressEl.addEventListener('touchstart', function (e) { self._onScrubStart(e); });

        this.progressEl.addEventListener('mousemove', function (e) { self._onProgressHover(e); });
        this.progressEl.addEventListener('mouseleave', function () {
            self.progressTooltip.style.opacity = '0';
        });

        this._boundKeyDown = this._onKeyDown.bind(this);
        this._boundScrubMove = this._onScrubMove.bind(this);
        this._boundScrubEnd = this._onScrubEnd.bind(this);

        document.addEventListener('keydown', this._boundKeyDown);
        document.addEventListener('mousemove', this._boundScrubMove);
        document.addEventListener('touchmove', this._boundScrubMove, { passive: false });
        document.addEventListener('mouseup', this._boundScrubEnd);
        document.addEventListener('touchend', this._boundScrubEnd);
    };

    VideoPlayer.prototype.destroy = function () {
        var video = this.video;
        this._cancelIdleTimer();
        document.removeEventListener('fullscreenchange', this._onFullscreenChange);
        document.removeEventListener('webkitfullscreenchange', this._onFullscreenChange);
        if (this._boundKeyDown) {
            document.removeEventListener('keydown', this._boundKeyDown);
        }
        if (this._boundScrubMove) {
            document.removeEventListener('mousemove', this._boundScrubMove);
            document.removeEventListener('touchmove', this._boundScrubMove);
        }
        if (this._boundScrubEnd) {
            document.removeEventListener('mouseup', this._boundScrubEnd);
            document.removeEventListener('touchend', this._boundScrubEnd);
        }
        if (video._smPlayer) {
            delete video._smPlayer;
        }
    };

    VideoPlayer.prototype.applySettings = function () {
        var s = this.settings;
        if (s.volume !== undefined) {
            this.video.volume = clamp(s.volume, 0, 1);
            this.volumeSlider.value = Math.round(s.volume * 100);
        }
        if (s.muted !== undefined) {
            this.video.muted = s.muted;
            this.volumeBeforeMute = s.volumeBeforeMute || 1;
        }
        if (s.speed !== undefined) {
            this.video.playbackRate = s.speed;
            this.speedSelect.value = String(s.speed);
        }
        if (s.loop !== undefined) {
            this.video.loop = s.loop;
            this.loopBtn.classList.toggle('active', s.loop);
        }
        if (s.theater !== undefined) {
            var area = document.querySelector('#video-area');
            if (area) area.classList.toggle('theater-mode', s.theater);
            this.theaterBtn.classList.toggle('active', s.theater);
        }
        this._syncVolumeIcon();
        this._syncPlayBtn();
    };

    VideoPlayer.prototype._syncVolumeIcon = function () {
        if (this.video.muted || this.video.volume === 0) {
            this.muteBtn.innerHTML = SVG.volumeMute;
        } else if (this.video.volume < 0.5) {
            this.muteBtn.innerHTML = SVG.volumeLow;
        } else {
            this.muteBtn.innerHTML = SVG.volumeHigh;
        }
    };

    VideoPlayer.prototype._syncPlayBtn = function () {
        var icon = this.video.paused ? SVG.play : SVG.pause;
        this.playBtn.innerHTML = icon;
        this.centerPlay.innerHTML = icon;
        this.centerPlay.classList.toggle('visible', this.video.paused);
        this.container.classList.toggle('paused', this.video.paused);
        this.container.classList.toggle('playing', !this.video.paused);
    };

    VideoPlayer.prototype.togglePlay = function () {
        if (this.video.paused) {
            var p = this.video.play();
            if (p && p.catch) p.catch(function () {});
        } else {
            this.video.pause();
        }
    };

    VideoPlayer.prototype.seek = function (delta) {
        this.video.currentTime = clamp(this.video.currentTime + delta, 0, this.video.duration || 0);
        this._showSeekFeedback(delta);
    };

    VideoPlayer.prototype.setVolume = function (val) {
        this.video.volume = clamp(val, 0, 1);
        this.video.muted = (val === 0);
        this.volumeSlider.value = Math.round(val * 100);
        this._syncVolumeIcon();
        this.settings.volume = this.video.volume;
        this.settings.muted = this.video.muted;
        this.settings.volumeBeforeMute = this.volumeBeforeMute;
        saveSettings(this.settings);
    };

    VideoPlayer.prototype.toggleMute = function () {
        if (this.video.muted) {
            this.video.muted = false;
            if (this.video.volume === 0) {
                this.setVolume(this.volumeBeforeMute || 1);
            }
        } else {
            this.volumeBeforeMute = this.video.volume;
            this.video.muted = true;
        }
        this._syncVolumeIcon();
        this.settings.muted = this.video.muted;
        this.settings.volumeBeforeMute = this.volumeBeforeMute;
        saveSettings(this.settings);
    };

    VideoPlayer.prototype.setSpeed = function (speed) {
        this.video.playbackRate = speed;
        this.speedSelect.value = String(speed);
        this.settings.speed = speed;
        saveSettings(this.settings);
        this._showSpeedIndicator();
    };

    VideoPlayer.prototype.cycleSpeed = function (direction) {
        var opts = this.speedSelect.options;
        var idx = this.speedSelect.selectedIndex;
        idx = clamp(idx + direction, 0, opts.length - 1);
        this.setSpeed(parseFloat(opts[idx].value));
    };

    VideoPlayer.prototype.toggleLoop = function () {
        this.video.loop = !this.video.loop;
        this.loopBtn.classList.toggle('active', this.video.loop);
        this.settings.loop = this.video.loop;
        saveSettings(this.settings);
    };

    VideoPlayer.prototype.toggleTheater = function () {
        var area = document.querySelector('#video-area');
        if (!area) return;
        area.classList.toggle('theater-mode');
        var active = area.classList.contains('theater-mode');
        this.theaterBtn.classList.toggle('active', active);
        this.settings.theater = active;
        saveSettings(this.settings);
    };

    VideoPlayer.prototype.toggleFullscreen = function () {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            var el = this.container;
            if (el.requestFullscreen) {
                el.requestFullscreen();
            } else if (el.webkitRequestFullscreen) {
                el.webkitRequestFullscreen();
            }
        }
    };

    VideoPlayer.prototype.togglePiP = function () {
        if (document.pictureInPictureElement) {
            document.exitPictureInPicture();
        } else if (document.pictureInPictureEnabled) {
            this.video.requestPictureInPicture().catch(function () {});
        }
    };

    VideoPlayer.prototype._getCurrentVideoIndex = function () {
        var links = findVideoLinks();
        var currentFilename = this._getCurrentFilename();
        for (var i = 0; i < links.length; i++) {
            if (links[i].href.indexOf(encodeURIComponent(currentFilename)) !== -1 ||
                links[i].href.indexOf(currentFilename) !== -1) {
                return i;
            }
        }
        return -1;
    };

    VideoPlayer.prototype._getCurrentFilename = function () {
        var playInput = document.getElementById('play_video');
        if (playInput) return playInput.value;
        var src = this.video.currentSrc || this.video.src;
        var parts = src.split('/');
        return decodeURIComponent(parts[parts.length - 1]);
    };

    VideoPlayer.prototype.nextVideo = function () {
        var links = findVideoLinks();
        var idx = this._getCurrentVideoIndex();
        if (idx >= 0 && idx < links.length - 1) {
            links[idx + 1].click();
        }
    };

    VideoPlayer.prototype.prevVideo = function () {
        var links = findVideoLinks();
        var idx = this._getCurrentVideoIndex();
        if (idx > 0) {
            links[idx - 1].click();
        }
    };

    VideoPlayer.prototype._onTimeUpdate = function () {
        var video = this.video;
        if (!isFinite(video.duration)) return;
        var pct = (video.currentTime / video.duration) * 100;
        this.progressFill.style.width = pct + '%';
        this.progressThumb.style.left = pct + '%';
        this.timeCurrent.textContent = formatTime(video.currentTime);
        this.timeDuration.textContent = formatTime(video.duration);

        var remaining = video.duration - video.currentTime;
        if (!video.loop && remaining < 15 && remaining > 0 && !video.paused) {
            this.nextOverlay.classList.add('visible');
        } else {
            this.nextOverlay.classList.remove('visible');
        }
    };

    VideoPlayer.prototype._onProgress = function () {
        var video = this.video;
        if (video.buffered.length > 0 && isFinite(video.duration)) {
            var end = video.buffered.end(video.buffered.length - 1);
            this.progressBuffer.style.width = (end / video.duration) * 100 + '%';
        }
    };

    VideoPlayer.prototype._onVolumeChange = function () {
        this.volumeSlider.value = Math.round(this.video.volume * 100);
        this._syncVolumeIcon();
    };

    VideoPlayer.prototype._onPlay = function () { this._syncPlayBtn(); this._startIdleTimer(); };
    VideoPlayer.prototype._onPause = function () { this._syncPlayBtn(); this.showControls(); this._cancelIdleTimer(); };
    VideoPlayer.prototype._onEnded = function () { this._syncPlayBtn(); };
    VideoPlayer.prototype._onWaiting = function () { this.container.classList.add('waiting'); };
    VideoPlayer.prototype._onCanPlay = function () { this.container.classList.remove('waiting'); };

    VideoPlayer.prototype._onFullscreenChange = function () {
        var isFS = !!(document.fullscreenElement || document.webkitFullscreenElement);
        this.container.classList.toggle('fullscreen', isFS);
        this.fullscreenBtn.innerHTML = isFS ? SVG.fullscreenExit : SVG.fullscreen;
    };

    VideoPlayer.prototype._onScrubStart = function (e) {
        this.isScrubbing = true;
        this.progressEl.classList.add('scrubbing');
        this._updateScrub(e);
        e.preventDefault();
    };

    VideoPlayer.prototype._onScrubMove = function (e) {
        if (!this.isScrubbing) return;
        this._updateScrub(e);
    };

    VideoPlayer.prototype._onScrubEnd = function () {
        if (!this.isScrubbing) return;
        this.isScrubbing = false;
        this.progressEl.classList.remove('scrubbing');
    };

    VideoPlayer.prototype._updateScrub = function (e) {
        var rect = this.progressEl.getBoundingClientRect();
        var clientX = e.touches ? e.touches[0].clientX : e.clientX;
        var pct = clamp((clientX - rect.left) / rect.width, 0, 1);
        if (isFinite(this.video.duration)) {
            this.video.currentTime = pct * this.video.duration;
        }
    };

    VideoPlayer.prototype._onProgressHover = function (e) {
        var rect = this.progressEl.getBoundingClientRect();
        var pct = clamp((e.clientX - rect.left) / rect.width, 0, 1);
        this.progressTooltip.style.left = (pct * 100) + '%';
        if (isFinite(this.video.duration)) {
            this.progressTooltip.textContent = formatTime(pct * this.video.duration);
        }
        this.progressTooltip.style.opacity = '1';
    };

    VideoPlayer.prototype.showControls = function () {
        this.isIdle = false;
        this.container.classList.remove('idle');
        this._startIdleTimer();
    };

    VideoPlayer.prototype.hideControls = function () {
        if (this.video.paused || this.isScrubbing) return;
        this.isIdle = true;
        this.container.classList.add('idle');
    };

    VideoPlayer.prototype._startIdleTimer = function () {
        this._cancelIdleTimer();
        var self = this;
        this.idleTimer = setTimeout(function () { self.hideControls(); }, IDLE_TIMEOUT);
    };

    VideoPlayer.prototype._cancelIdleTimer = function () {
        if (this.idleTimer) {
            clearTimeout(this.idleTimer);
            this.idleTimer = null;
        }
    };

    VideoPlayer.prototype._showSpeedIndicator = function () {
        var self = this;
        this.speedIndicator.textContent = this.video.playbackRate + 'x';
        this.speedIndicator.classList.add('visible');
        clearTimeout(this._speedTimer);
        this._speedTimer = setTimeout(function () {
            self.speedIndicator.classList.remove('visible');
        }, 1000);
    };

    VideoPlayer.prototype._showSeekFeedback = function (delta) {
        // briefly flash the center play icon with direction
        var video = this.video;
        var remaining = video.duration - video.currentTime;
        var displayTime = delta > 0 ? formatTime(video.currentTime) : formatTime(video.currentTime);
        this.centerPlay.innerHTML = '<span style="font-size:0.9rem;font-weight:700">' +
            (delta > 0 ? '+' : '') + delta + 's ' + displayTime + '</span>';
        this.centerPlay.classList.add('visible');
        var self = this;
        clearTimeout(this._seekTimer);
        this._seekTimer = setTimeout(function () {
            self._syncPlayBtn();
        }, 800);
    };

    VideoPlayer.prototype._onKeyDown = function (e) {
        var tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

        var key = e.key;

        if (key === ' ' || key === 'k') {
            e.preventDefault();
            this.togglePlay();
        } else if (key === 'ArrowLeft') {
            e.preventDefault();
            this.seek(e.shiftKey ? -SEEK_STEP_LARGE : -SEEK_STEP);
        } else if (key === 'ArrowRight') {
            e.preventDefault();
            this.seek(e.shiftKey ? SEEK_STEP_LARGE : SEEK_STEP);
        } else if (key === 'ArrowUp') {
            e.preventDefault();
            this.setVolume(this.video.volume + 0.05);
        } else if (key === 'ArrowDown') {
            e.preventDefault();
            this.setVolume(this.video.volume - 0.05);
        } else if (key === 'f' || key === 'F') {
            e.preventDefault();
            this.toggleFullscreen();
        } else if (key === 'm' || key === 'M') {
            e.preventDefault();
            this.toggleMute();
        } else if (key === 't' || key === 'T') {
            e.preventDefault();
            this.toggleTheater();
        } else if (key === 'l' || key === 'L') {
            e.preventDefault();
            this.toggleLoop();
        } else if (key === '>' || key === '.') {
            e.preventDefault();
            this.cycleSpeed(1);
        } else if (key === '<' || key === ',') {
            e.preventDefault();
            this.cycleSpeed(-1);
        } else if (key === 'Home') {
            e.preventDefault();
            this.video.currentTime = 0;
        } else if (key === 'End') {
            e.preventDefault();
            if (isFinite(this.video.duration)) this.video.currentTime = this.video.duration;
        } else if (key === 'N' && e.shiftKey) {
            e.preventDefault();
            this.nextVideo();
        } else if (key === 'P' && e.shiftKey) {
            e.preventDefault();
            this.prevVideo();
        } else if (key >= '0' && key <= '9') {
            e.preventDefault();
            var pct = parseInt(key) / 10;
            if (isFinite(this.video.duration)) this.video.currentTime = pct * this.video.duration;
        }
    };

    function initPlayers() {
        var videos = document.querySelectorAll('#video-area video');
        for (var i = 0; i < videos.length; i++) {
            new VideoPlayer(videos[i]);
        }
    }

    function destroyPlayers() {
        var players = document.querySelectorAll('#video-area video');
        for (var i = 0; i < players.length; i++) {
            if (players[i]._smPlayer) {
                players[i]._smPlayer.destroy();
            }
        }
    }

    document.addEventListener('DOMContentLoaded', initPlayers);
    document.addEventListener('htmx:beforeSwap', function (e) {
        if (e.detail.target && e.detail.target.id === 'content') {
            destroyPlayers();
        }
    });
    document.addEventListener('htmx:afterSettle', function (e) {
        if (e.detail.target && e.detail.target.id === 'content') {
            initPlayers();
        }
    });
})();
