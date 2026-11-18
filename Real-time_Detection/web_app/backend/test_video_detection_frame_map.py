import unittest

from video_detection_frame_map import (
    video_detection_frame_filter,
    video_detection_frame_match,
    video_detection_frames,
)


class VideoDetectionFrameMapTests(unittest.TestCase):
    def test_video1_uses_attachment_frame_numbers(self):
        self.assertEqual(video_detection_frames("video1.mp4"), (60, 75, 90, 105, 120))

    def test_listed_video_without_frames_keeps_normal_detection(self):
        self.assertEqual(video_detection_frames("video4.mp4"), ())
        self.assertEqual(video_detection_frames("video26.mp4"), ())
        self.assertIsNone(video_detection_frame_filter("video4.mp4"))
        self.assertIsNone(video_detection_frame_filter("video26.mp4"))

    def test_filename_outside_attachment_keeps_normal_detection(self):
        self.assertIsNone(video_detection_frames("other-video.mp4"))
        self.assertIsNone(video_detection_frame_filter("other-video.mp4"))
        self.assertEqual(video_detection_frame_match("other-video.mp4"), (False, None))

    def test_match_state_distinguishes_empty_entry_from_unmatched_name(self):
        self.assertEqual(video_detection_frame_match("video4.mp4"), (True, ()))
        self.assertEqual(
            video_detection_frame_match("video1.mp4"),
            (True, (60, 75, 90, 105, 120)),
        )
        self.assertEqual(
            video_detection_frame_filter("video1.mp4"),
            (60, 75, 90, 105, 120),
        )

    def test_browser_fake_path_uses_the_uploaded_filename(self):
        self.assertEqual(
            video_detection_frame_match(r"C:\\fakepath\\VIDEO1.MP4"),
            (True, (60, 75, 90, 105, 120)),
        )

    def test_mapping_uses_filename_case_insensitively(self):
        self.assertEqual(video_detection_frames("VIDEO1.MP4"), (60, 75, 90, 105, 120))


if __name__ == "__main__":
    unittest.main()
