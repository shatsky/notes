---
title: FFmpeg and generic multimedia notes
summary: Useful FFmpeg commands, common formats reference
---

Practical tasks to cover

- downloading and lossless cutting of web videos
- TODO creating "video bookmarks", i. e. playable playlist-like files which refer to time interval in single video file and can be used to quickly create standalone video file for sharing; see VLC-specific M3U `#EXTVLCOPT:start-time`/`stop-time`, XSPF
- TODO generic understanding of a/v sync in popular formats
- TODO lossless transcoding of JPEG into more space efficient JPEG-XL
- TODO low latency playback of V4L streams (gstreamer?)

## Useful FFmpeg commands

**Download HLS (HTTP Live Streaming) videos**: `ffmpeg -i "${url_of_m3u8}" -codec copy -seg_max_retry 2147483647 "${output_filename}.mp4"`

You may remember "good" old times when web videos embedded in webpages were fetched by browser in single queries as "normal" video files. At the dawn of popularity of YouTube and other \*Tubes and \*Hubs, Adobe Flash Player based web video players were popular, which played FLV files, allowing to capture request URL via browser dev tools and download the file. Then circa 2007 HTML5 \<video\> tag was introduced and in many cases it became possible to save video simply from context menu. However, for certain reasons, industry wanted technology which would allow streaming videos as sequences of short "segment" files, each fetched separately. Today, on many websites, even if you get to default context menu of \<video\> element and try to download, browser will, in best case, download only short fragment; in fact, there's no single video file being fetched, full or partial, during playback; what you will see in browser dev tools, depends. Some websites use proprietary solutions which require "targeted" solutions for video downloading (yt-dlp currently being the "Swiss knife" for these); most websites, however, adopted HLS (HTTP Live Streaming), introduced by Apple circa 2017. If you open browser dev tools on such website and start playback, you will see query to .m3u8 file and then many queries to .ts files. Well, .m3u8 is just M3U playlist in UTF-8, and .ts are "MPEG Transport Stream segments" listed in it, containing fragments of H.264 video stream and audio stream encoded with one of several supported codecs. FFmpeg allows to fetch the playlist with all segments listed in it and copy video and audio streams (without any lossy transcoding) to "normal" video file (MP4 being "native" container for H.264) in one command.

Note: some recommend adding `-bsf:a aac_adtstoasc` to convert [ADTS](https://wiki.multimedia.cx/index.php/ADTS) to [ASC](https://wiki.multimedia.cx/index.php/MPEG-4_Audio#Audio_Specific_Config) (audio stream metadata), but https://ffmpeg.org/ffmpeg-bitstream-filters.html#aac_005fadtstoasc states it's auto-inserted for MP4.

Note: this is only applicable for DRM-free videos.

Note: by default ffmpeg skips segment if request fails. Best possible thing to prevent getting broken files currently seems to set seg_max_retry to MAX_INT, https://github.com/FFmpeg/FFmpeg/blob/94f2274a8b61438572f0873ccf430e55ce0e0e2b/libavformat/hls.c#L230C9-L230C22

**Cut videos at defined time interval**: `ffmpeg -ss ${hh_start}:${mm_start}:${ss_start} -to ${hh_end}:${mm_end}:${ss_end} -i "${input_file}" -c copy "${output_file}"`

Note: most frames in video streams are stored as "deltas", and only some are full "keyframes"; video has to start with "keyframe", and cutting time_start will likely not match one, so preceding frames starting with previous keyframe will be copied too; audio stream doesn't have something like "keyframes" synchronized with video ones; therefore, upon copying from MP4 to MP4, ffmpeg can create file with video or audio starting not exactly from 0s, causing minor playback issues in some players. Observations:

- ffplay (FFmpeg reference player impl) starts playback from ~time_start moment, both video and audio
- Firefox plays some frames of video preceding ~time_start without sound, sound starts at ~time_start
- mpv (based on FFmpeg) also plays some frames of video preceding ~time_start without sound, but after the sound starts it increases video playback speed for a moment, emitting stderr warning about a/v sync issue, then playback proceeds normally

Proposed solutions are:

- adding `-avoid_negative_ts make_zero`
- using MKV target container
- somehow explicitly cutting on keyframes

All these solutions seem to result in creation of file which has both video and audio starting from preceding keyframe (synchronized, of course)

**Encode video to H.264**: `ffmpeg -i "${input_file}" -c:v libx264 "${output_file}"`

If output_file is *.mp4, ffmpeg picks H.264 by default

**Cut videos at defined time interval and render subtitles into video**: `ffmpeg -ss ${hh_start}:${mm_start}:${ss_start} -copyts -to ${hh_end}:${mm_end}:${ss_end} -i "${input_file}" -ss ${hh_start}:${mm_start}:${ss_start} -vf subtitles="${input_file_containing_subtitles}:si={subtitles_track_index}" "${output_file}"`

`${input_file_containing_subtitles}` is required even if subtitle tracks are contained in input video file, i. e. if duplicating `${input_file}`

`:si={subtitles_track_index}` is only required if there are multiple subtitle tracks and needed track is not the 1st

`-copyts` and 2nd `-ss` are required

### Reference of used FFmpeg cmdline options

- `-codec copy`: copy streams without re-encoding, i. e. without added loss of quality

## Formats

"Video file format" is usually combination of

- video coding format
- audio coding format
- some metadata format(s)
- container (muxer) format, multiplexing all above so that they can be stored in single file and played synchronously; some container formats are developed to contain only specific stream formats, others are more generic

Development of all these seems to be mostly driven by development of video codecs (obviously being the most complex part of the stack)

### Web video file formats

To put simply:

| Name | Meaning | Origins |
| ---  | ---     | ---     |
| MP4  | MP4 container containing H.264/H.265 video stream and AAC audio stream | From "world standartization authorities" ISO/IEC/MPEG/ITU-T/etc., initially supported in major proprietary browsers developed by commercial companies since HTML5 \<video\> tag was introduced |
| Ogg  | Ogg container containing Theora video stream and Vorbis audio stream | Alternative pushed by FOSS community because MP4/H.264 standards are not truly free, making them problematic to implement for non-commercial developers and just incompatible with FOSS philosophy; practically obsoleted by WebM |
| WebM | MKV container containing VP8/VP9/AV1 video stream and Vorbis/Opus audio stream| Alternative pushed by Google because commercial companies opposed to implementing Ogg/Theora; Google just bought On2, company which had developed Theora, originally known as VP3, made all its then-latest competitive VP8 codec public domain too, and continued developing it, later as part of AOMedia alliance; MKV container chosen for multiplexing had been open standard from the beginning |

Full reality is more complicated, for each format there are more codecs (which are extremely rarely used), but at the same time some major browsers don't support even some of those mentioned (or did in the past but have dropped support). HTML5 itself doesn't actually define required formats which should be supported for \<video\> (but allows to provide several different files)

### Video and image coding formats

| Name           | Org              | Year | Notes |
| ---            | ---              | ---  | ---   |
| H.264 aka AVC  | ISO and others   | 2004 | "MPEG-4 Part 10: Advanced Video Coding", name "H.264" being its ITU-T number; currently most popular because hardware for efficient decoding is most available in consumer devices |
| H.265 aka HEVC | ISO and others   | 2013 | "MPEG-H Part 2: High Efficiency Video Coding", name "H.265" being its ITU-T number |
| VP8            | On2 -> Google    | 2008 | Bought by Google with its developer company to create WebM video format; also used in WebP image format |
| VP9            | Google           | 2012 | Subsequent development of VP8 |
| Theora aka VP3 | On2 -> Xiph.org  | 2004 | To be precise, VP3 and Theora are not same thing; On2 had released VP3 into public domain, and Xiph.org "improved" it, creating "superset" codec (Theora implementations can decode VP3 streams, but original VP3 can't decode Theora streams) |
| AV1            | Google -> AOMedia | 2018 | Created as successor to Google VP9 by AOMedia, consortium created by key industry players incl. Amazon, Google, Intel, Microsoft and Mozilla for development of open, royalty-free web multimedia standards; also used in AVIF image format |
| JPEG           | JPEG             | 1992 | JPEG is actually image codec, but it's technically possible to use image codecs for compressing video streams (quite inefficiently as these can't handle interframe redundancy); while new image formats based on "true" video codecs are becoming popular, JPEG is still most common one, and even still relevant as video codec, used by many cheap webcams and video capture devices (chips for hardware JPEG compression are much more affordable then ones for "true" video codecs), stream of JPEG-compressed frames known as "MJPEG video" |
| JPEG-XL        |                  | 2022 | Image codec which is more efficient than JPEG and allows "lossless recompression of lossy-compressed JPEG", so that existing JPEG files can be compressed ~20% more without quality loss; however Google decided to oppose it, removing initially added support from Chrome and ignoring requests to re-add it |

*MPEG which is appearing a lot in names of multimedia standards is actually "Moving Picture Experts Group", joint entity of ISO and IEC, "world standartization authorities", something like UN for tech corporations, which develop shared standards via it; these standards can be accessed by anyone, but not for free, and can and usually are covered by patents, owners of which can demand royalties for using tech solutions covered by them*

### Container and file formats

*Note: some container formats are defined on top of other, more generic ones, "extending" them or, from other point of view, "limiting" variety of data which they can contain; some of these "base" container formats can encode information about contained data types and can be used as file formats themselves, meaning that "extended" ones are merely "convenience aliases" indicating subsets supported in certain domains; others don't*

| Name | Extends | Filename ext | Contained video streams | Contained audio streams | Org | Year | Notes |
| ---  | ---     | ---          | ---                     | ---                     | --- | ---  | ---   |
| ISOBMFF |      |              |                         |                         | ISO and others | 2004 | "MPEG-4 Part 12: ISO base media file format", base container format, developed as "generalization" of MP4 |
| MP4  | ISOBMFF | .mp4         | usually H.265 or H.264  | usually AAC             | ISO and others | 2001 | "MPEG-4 Part 14: MP4 file format", originally based on Apple QuickTime file format (QTFF, .mov), .mp4 files can contain streams of many different types, but it seems that MP4 standard covers specifically MPEG-4 streams, and anything else means it's actually different sub/superset of ISOBMFF, also they share "Registration Authority" https://mp4ra.org/ |
| MKV  |         | .mkv         | virtually any           | virtually any           | Matroska project | 2002 | "Matroska", totally generic container and file format, open standard |
| WebM | MKV     | .webm        | VP8/VP9/AV1             | Vorbis/Opus             | Google | 2010 ||
| Ogg  |         | .ogg         | usually Theora          | usually Vorbis or FLAC  | Xiph.org | 2003 ||
| RIFF |         |              |                         |                         | Microsoft, IBM | 1991 | base container format for many formats, including WebP and historically relevant (non-Web) AVI ("Audio Video Interleave", popular for storing videos in 90s-00s, usually containing MPEG-1/2/4 Part 2 video streams) and WAV ("Waveform Audio File Format", popular for storing audio recordings in 90s-00s, usually containing LPCM audio stream) |
| WebP | RIFF    | .webp        | VP8 (single frame)      | -                       | Google | 2010 ||
| HEIF | ISOBMFF | .heif        |                         | -                       | ISO and others | 2015 | "MPEG-H Part 12: High Efficiency Image File Format", container and file format designed for images and image sequences |
| HEIC | HEIF    | .heic        | H.265 (single frame)    | -                       | ISO and others | 2015 ||
| AVIF | HEIF    | .avif        | AV1 (single frame)      | -                       | AOMedia | 2019 ||
| JFIF |         | .jpg         | JPEG (single frame)     | -                       || 1992 | "JPEG File Interchange Format" aka JPEG file format, there's also EXIF "EXchangeable Image File format" created later by camera manufacturers, which is almost identical but has some formal incompatibility, in practice "mixed JFIF+EXIF" seems to be used everywhere, with metadata encoded as per EXIF spec |
