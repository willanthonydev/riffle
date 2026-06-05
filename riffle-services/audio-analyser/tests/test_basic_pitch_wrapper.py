from audio_analyser.basic_pitch_wrapper import normalize_note_events


def test_normalize_tuple_note_events_sorts_and_converts_to_milliseconds():
    notes = normalize_note_events(
        [
            (0.5, 0.75, 67, 0.7),
            (0.1, 0.25, 64, 0.9),
        ]
    )

    assert [note.start_ms for note in notes] == [100, 500]
    assert [note.end_ms for note in notes] == [250, 750]
    assert [note.pitch_midi for note in notes] == [64, 67]
    assert [note.confidence for note in notes] == [0.9, 0.7]


def test_normalize_dict_note_events_ignores_out_of_range_confidence():
    notes = normalize_note_events(
        [
            {
                "start_time_s": 0.1,
                "end_time_s": 0.2,
                "pitch_midi": 64,
                "amplitude": 12,
            }
        ]
    )

    assert len(notes) == 1
    assert notes[0].confidence is None

