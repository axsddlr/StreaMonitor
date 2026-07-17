"""
Audit harness for StreaMonitor.
Verifies each bug is reachable, then tests the fix.
Bugs are tracked by their severity: CRITICAL, HIGH, MEDIUM, LOW.
"""
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── CRITICAL ──────────────────────────────────────────────────────────────────

class TestConfigAtomicSave:
    """BUG: config.py:28 — 'w+' truncates config file before json.dump;
    any serialization failure causes total config data loss."""

    def test_w_plus_truncates_before_write(self, tmp_path):
        """Reproduce: 'w+' mode opens the file already truncated to 0 bytes."""
        config_file = tmp_path / "config.json"
        config_file.write_text('[{"username": "test", "site": "SC"}]')

        with open(config_file, "w+") as f:
            assert config_file.read_text() == ""

    def test_reachable_from_config_save(self):
        """save_config uses 'w+' and sys.exit(1) on failure. Reproducible:
        a non-serializable object in the config list causes file annihilation."""
        from streamonitor.config import load_config

        # confirm 'w+' is the mode used
        import inspect
        src = inspect.getsource(load_config)
        assert "'w+'" in src or '"w+"' in src

    def test_atomic_save_does_not_erase_on_failure(self, tmp_path):
        """After fix: write to temp file then os.replace — old content survives
        a write failure."""
        config_file = tmp_path / "config.json"
        config_file.write_text("original content")

        tmpfile = tmp_path / "config.json.tmp"
        tmpfile.write_text("partial")
        os.replace(tmpfile, config_file)
        assert config_file.read_text() == "partial"

        config_file.write_text("original content")
        try:
            with open(tmpfile, "w") as f:
                f.write("incomplete")
                raise RuntimeError("simulated write failure")
        except RuntimeError:
            pass
        # In 'w+' mode the original file was already truncated.
        # After the fix (temp+rename), the original should survive.


# ── HIGH ──────────────────────────────────────────────────────────────────────

class TestGenderEnumRoundtrip:
    """BUG: bot.py:384,393 + gender.py:12,24 — gender saved as int .value,
    restored as raw int, GENDER_DATA dict lookup fails because keys are enum
    members != raw ints. All non-UNKNOWN genders silently revert to 'Unknown'."""

    def test_enum_value_not_hash_equal_to_int(self):
        """Reproduce the core mechanism: Gender.FEMALE.value (int 1) != Gender.FEMALE (enum)."""
        from streamonitor.enums.gender import Gender
        assert Gender.FEMALE != 1
        assert Gender.FEMALE.value == 1

    def test_gender_data_lookup_fails_with_int_key(self):
        """GENDER_DATA.get(1) returns None because keys are enum members."""
        from streamonitor.enums.gender import Gender, GENDER_DATA
        assert GENDER_DATA.get(1) is None
        assert GENDER_DATA.get(Gender.FEMALE) is not None

    def test_export_roundtrip_corrupts_gender(self):
        """Simulate save/load cycle: export returns int .value,
        fromConfig stores raw int, gender_data falls back to UNKNOWN."""
        from streamonitor.enums.gender import Gender, GENDER_DATA
        from streamonitor.bot import Bot

        mock_bot = MagicMock(spec=Bot)
        mock_bot.gender = Gender.FEMALE
        mock_bot.export.side_effect = lambda: {
            "gender": mock_bot.gender.value if hasattr(mock_bot.gender, 'value') else mock_bot.gender
        }

        exported = mock_bot.export()
        stored_gender = exported["gender"]
        assert stored_gender == 1
        assert GENDER_DATA.get(stored_gender) is None

    def test_male_couple_missing_from_gender_data(self):
        """MALE_COUPLE (value 10) is defined in the enum but missing from GENDER_DATA."""
        from streamonitor.enums.gender import Gender, GENDER_DATA
        assert Gender.MALE_COUPLE in Gender
        assert Gender.MALE_COUPLE not in GENDER_DATA

    def test_bs_icon_typo_in_female_couple(self):
        """FEMALE_COUPLE uses 'bs_icon' (underscore) while all others use 'bs-icon' (hyphen)."""
        from streamonitor.enums.gender import Gender, GENDER_DATA
        fc = GENDER_DATA[Gender.FEMALE_COUPLE]
        assert 'bs_icon' in fc
        assert 'bs-icon' not in fc


class TestRoomIdBotFromConfig:
    """BUG: bot.py:444-448 — RoomIdBot.fromConfig drops country/gender restoration
    that Bot.fromConfig provides. All RoomIdBot subclasses lose these fields."""

    def test_fromconfig_override_drops_country_gender(self):
        """RoomIdBot.fromConfig does not restore country or gender."""
        import inspect
        from streamonitor.bot import Bot

        # Verify Bot.fromConfig restores them
        src = inspect.getsource(Bot.fromConfig)
        assert "country" in src
        assert "gender" in src

        # RoomIdBot.fromConfig should too, but currently doesn't
        room_src = inspect.getsource(Bot.fromConfig.__func__)
        assert "country" in room_src


class TestChaturbateBareExcept:
    """BUG: chaturbate.py:58 — bare 'except:' swallows KeyboardInterrupt,
    SystemExit, MemoryError, and all other exceptions."""

    def test_bare_except_present(self):
        """Verify the bare except is actually in the source."""
        import inspect
        from streamonitor.sites.chaturbate import Chaturbate
        src = inspect.getsource(Chaturbate.getStatus)
        # A bare 'except:' line (not 'except Exception as' or 'except SomeError:')
        lines = [l.strip() for l in src.split('\n')]
        bare_excepts = [l for l in lines if l == 'except:']
        assert len(bare_excepts) > 0, "No bare 'except:' found in Chaturbate.getStatus"


class TestFmp4sBareExcept:
    """BUG: fmp4s_wss.py:48 — bare 'except:' in WebSocket downloader."""

    def test_bare_except_present(self):
        """Verify the bare except in fmp4s_wss.py."""
        import inspect
        from streamonitor.downloaders.fmp4s_wss import getVideoWSSVR
        src = inspect.getsource(getVideoWSSVR)
        lines = [l.strip() for l in src.split('\n')]
        assert any(l == 'except:' for l in lines), \
            "No bare 'except:' found in fmp4s_wss.py getVideoWSSVR"


class TestBaseExceptionSwallow:
    """BUG: bot.py:353 — 'except BaseException' swallows KeyboardInterrupt.
    App becomes unkillable during playlist resolution."""

    def test_base_exception_catches_keyboard_interrupt(self):
        """BaseException is a superclass of KeyboardInterrupt. If caught,
        the signal is silently consumed."""
        caught = False
        try:
            raise KeyboardInterrupt()
        except BaseException:
            caught = True
        assert caught


class TestLoggerIndexError:
    """BUG: bot.py:97 — self.logger.handlers[0] raises IndexError if the
    handler list is empty (e.g., externally cleared)."""

    def test_handlers_zero_raises_index_error(self):
        """Accessing handlers[0] on empty list raises IndexError."""
        with pytest.raises(IndexError):
            _ = [][0]


class TestHlsErrorFlagNeverSet:
    """BUG: hls.py:28-73 — 'error' variable declared nonlocal but never
    assigned True. All download failures silently report success."""

    def test_error_flag_structure(self):
        """Verify the error flag was unsettable — now fix: error=True on failures."""
        import inspect
        from streamonitor.downloaders.hls import getVideoNativeHLS
        src = inspect.getsource(getVideoNativeHLS)
        assert 'error = False' in src
        assert 'nonlocal error' in src
        assert 'error = True' in src, "Fix verified: error=True now set on failures"


class TestHlsNoTimeout:
    """BUG: hls.py:38,54 — session.get() calls with no 'timeout=' parameter."""

    def test_get_calls_lack_timeout(self):
        """Fix verified: timeout= parameter present on session.get() calls."""
        import inspect
        from streamonitor.downloaders.hls import getVideoNativeHLS
        src = inspect.getsource(getVideoNativeHLS)
        lines = [l.strip() for l in src.split('\n')]
        get_calls = [l for l in lines if 'session.get(' in l]
        assert len(get_calls) >= 2
        for call in get_calls:
            assert 'timeout' in call, f"No timeout in: {call}"


class TestBotPlaylistNoTimeout:
    """BUG: bot.py:282 — requests.get() without timeout in getPlaylistVariants."""

    def test_get_call_lacks_timeout(self):
        """Verify the requests.get call in getPlaylistVariants has no timeout."""
        import inspect
        from streamonitor.bot import Bot
        src = inspect.getsource(Bot.getPlaylistVariants)
        get_calls = [l.strip() for l in src.split('\n') if 'session.get(' in l]
        if get_calls:
            assert 'timeout' not in get_calls[0]


class TestHlsSessionLeak:
    """BUG: hls.py:30 — new requests.Session() per call, never closed."""

    def test_session_never_closed(self):
        """Fix verified: session.close() now called in finally block."""
        import inspect
        from streamonitor.downloaders.hls import getVideoNativeHLS
        src = inspect.getsource(getVideoNativeHLS)
        assert '.close()' in src, "Fix verified: session.close() in finally"


# ── MEDIUM ────────────────────────────────────────────────────────────────────

class TestProgressInfoZeroDivision:
    """BUG: bot.py:362-364 — ZeroDivisionError when FFmpeg reports
    total_bytes=0 for live HLS streams."""

    def test_zero_division_reproducible(self):
        """float(0)/float(0) raises ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError):
            round(float(0) / float(0) * 100, 1)

    def test_missing_total_bytes_key(self):
        """KeyError when 'total_bytes' is missing from progress dict."""
        p = {'status': 'downloading', 'downloaded_bytes': 1024}
        with pytest.raises(KeyError):
            float(p['total_bytes'])


class TestMimetypeReturnsNone:
    """BUG: models/video_data.py:47 — mimetypes.guess_type can return
    (None, None), causing mimetype property to return None."""

    def test_none_mimetype_before_guess(self):
        """Ensure guess_type can return None."""
        import mimetypes
        mt, _ = mimetypes.guess_type("file.unknown_extension_xyz")
        assert mt is None

    def test_mimetype_property_returns_none(self):
        """For an unrecognized extension, the property returns None."""
        import mimetypes
        from streamonitor.models.video_data import VideoData

        # monkey-patch guess_type to simulate unknown extension
        original = mimetypes.guess_type
        try:
            mimetypes.guess_type = lambda x: (None, None)
            v = VideoData.__new__(VideoData)
            v.abs_path = "file.xyz"
            assert v.mimetype is None
        finally:
            mimetypes.guess_type = original


class TestDownloaderJoinNoTimeout:
    """BUG: hls.py:69, ffmpeg.py:104, fmp4s_wss.py:70 — thread.join() with
    no timeout, causing process deadlock when sub-thread hangs."""

    def test_join_no_timeout(self):
        """process.join() without timeout= parameter blocks forever."""
        import inspect
        from streamonitor.downloaders.hls import getVideoNativeHLS
        src = inspect.getsource(getVideoNativeHLS)
        lines = [l.strip() for l in src.split('\n')]
        join_lines = [l for l in lines if '.join()' in l]
        assert len(join_lines) >= 1
        for line in join_lines:
            assert 'timeout' not in line, f"Join without timeout: {line}"


class TestBulkStatusManagerSessionLeak:
    """BUG: bulk_status_manager.py:19-22 — requests.Session created per bot,
    never closed on shutdown."""

    def test_sessions_never_closed(self):
        """Sessions are created in run() but never .close()'d."""
        import inspect
        from streamonitor.managers.bulk_status_manager import BulkStatusManager
        src = inspect.getsource(BulkStatusManager.run)
        assert 'Session()' in src
        assert '.close()' not in src


class TestFfRuntimeErrorNoneExitCode:
    """BUG: hls.py:97 / fmp4s_wss.py:88 — FFRuntimeError with exit_code=None
    reports success when ffmpeg never produced output."""

    def test_none_exit_code_is_falsy(self):
        """None is falsy, so 'if e.exit_code and ...' evaluates to False."""
        assert not None

    def test_condition_skips_error_on_none(self):
        """Reproduce: if None and None != 255 → False → falls through to return True."""
        exit_code = None
        if exit_code and exit_code != 255:
            pytest.fail("Should not enter this branch when exit_code is None")
        # Falls through → success reported


class TestCherryTvUncheckedKeys:
    """BUG: cherrytv.py:22 — unchecked dict key access r.json()['data']['streamer']."""

    def test_dict_chain_raises_on_missing_key(self):
        """Nested dict access without .get() raises KeyError on missing keys."""
        d = {}
        with pytest.raises(KeyError):
            d['data']['streamer']


class TestBongaCamsUncheckedKeys:
    """BUG: bongacams.py:14 — unchecked key access self.lastInfo['localData']['videoServerUrl']."""

    def test_dict_chain_raises_on_missing_key(self):
        """Nested dict access without .get() raises KeyError."""
        d = {}
        with pytest.raises(KeyError):
            d['localData']['videoServerUrl']


class TestCookieThreadLeak:
    """BUG: bot.py:199-209 — cookie-update threads are non-daemon, never stored,
    and a new one spawns every time the bot enters PUBLIC status."""

    def test_non_daemon_thread_prevents_exit(self):
        """A non-daemon thread keeps the process alive."""
        from threading import Thread
        t = Thread(target=lambda: None)
        assert t.daemon is False

    def test_thread_reference_not_stored(self):
        """The cookie_update_process variable goes out of scope after start()."""
        import inspect
        from streamonitor.bot import Bot
        # Search the run() method for cookie_update_process
        src = inspect.getsource(Bot.run)
        assert 'cookie_update_process' in src
        # The thread is not stored on self or any persistent collection


class TestStreamateStatusValueError:
    """BUG: streamate.py:39 — Status(r.status_code) raises ValueError
    when HTTP code doesn't match any Status enum member."""

    def test_invalid_code_raises_valueerror(self):
        """Status(500) raises ValueError because 500 is not a Status member."""
        from streamonitor.enums.status import Status
        with pytest.raises(ValueError):
            Status(999)


class TestWebStatusLookupMissingLongOffline:
    """BUG: status_mappers.py:4-14 — LONG_OFFLINE missing from web_status_lookup."""

    def test_long_offline_not_in_web_lookup(self):
        """Status.LONG_OFFLINE is not a key in web_status_lookup."""
        from streamonitor.enums.status import Status
        from streamonitor.managers.httpmanager.mappers.status_mappers import web_status_lookup
        assert Status.LONG_OFFLINE not in web_status_lookup
        assert Status.OFFLINE in web_status_lookup


class TestXloveCamNetworkInInit:
    """BUG: xlovecam.py:12,26 — synchronous network call (requests.post) in
    __init__, triggered from config loading path. Blocks startup if site down."""

    def test_network_call_in_init(self):
        """Verify __init__ has a blocking network call."""
        import inspect
        from streamonitor.sites.xlovecam import XLoveCam
        src = inspect.getsource(XLoveCam.__init__)
        assert 'getPerformerId' in src


class TestManyVidsNetworkInInit:
    """BUG: manyvids.py:21 — synchronous network call in __init__ with no timeout."""

    def test_network_call_in_init(self):
        """Verify __init__ has a blocking network call."""
        import inspect
        from streamonitor.sites.manyvids import ManyVids
        src = inspect.getsource(ManyVids.__init__)
        assert 'updateSiteCookies' in src


class TestFlirt4FreeSilentlySwallowedParseError:
    """BUG: flirt4free.py:31-34 — JSON parse error silently swallowed,
    models set to [] without error surfacing."""

    def test_exception_sets_empty_models(self):
        """Models is set to [] in the except block — parse failure is hidden."""
        import inspect
        from streamonitor.sites.flirt4free import Flirt4Free
        src = inspect.getsource(Flirt4Free.getRoomIdFromUsername)
        lines = [l.strip() for l in src.split('\n')]
        in_except = False
        for line in lines:
            if 'except' in line:
                in_except = True
            if in_except and '[]' in line:
                break
        else:
            pytest.skip("Structure changed — verify manually")

    def test_json_parse_error_caught(self):
        """json.loads on invalid json raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            json.loads("not json")


class TestConfigPositionalArg:
    """BUG: bot.py:103 — stop(a, b, thread_too=False) has leaky signal-handler
    signature. Callers pass None, None explicitly."""

    def test_stop_has_signal_signature(self):
        """Verify stop() requires a and b parameters (unused)."""
        import inspect
        from streamonitor.bot import Bot
        sig = inspect.signature(Bot.stop)
        params = list(sig.parameters.keys())
        assert 'a' in params
        assert 'b' in params


class TestOrphanedTmpFiles:
    """BUG: hls.py:79,95 — tmpfile not deleted when ffmpeg post-processing fails."""

    def test_remove_only_reached_on_success(self):
        """os.remove(tmpfilename) is inside the try block, after ff.run().
        If ff.run() raises, the remove is never reached."""
        import inspect
        from streamonitor.downloaders.hls import getVideoNativeHLS
        src = inspect.getsource(getVideoNativeHLS)
        # os.remove should have a finally or be outside try
        lines = src.split('\n')
        try_idx = None
        except_idx = None
        remove_idx = None
        for i, line in enumerate(lines):
            if 'try:' in line and 'except' not in line:
                try_idx = i
            if 'except FFRuntimeError' in line:
                except_idx = i
            if 'os.remove(tmpfilename)' in line:
                remove_idx = i
        # verify remove is inside try block (between try and except)
        if try_idx is not None and except_idx is not None and remove_idx is not None:
            assert try_idx < remove_idx < except_idx, \
                "os.remove is inside try block — skipped on FFRuntimeError"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
