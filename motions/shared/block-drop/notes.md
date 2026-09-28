# Omarchy blocks drop in

One motion for every logo wallpaper: the Omarchy wordmark is built from its own pixel blocks. One block of the O blinks like a cursor, then each letter's blocks fall in from above the screen and stack up, bottom row first and left letter first. Each letter squashes on its baseline as its last block lands, a hop runs along the word, and by 4.4 s the frame is the wallpaper.

| Time | Beat |
|---|---|
| 0.35 | One block of the O blinks on, off and on, like a cursor |
| 0.95-2.9 | Blocks fall under gravity and bounce a little as they land; letters start 0.2 s apart |
| As each letter completes | It squashes on its baseline and springs back |
| 3.15 | A hop runs along the word, 0.1 s from letter to letter, each landing with a squash |
| 4.0-4.4 | Every wobble calms and the still fades in over the blocks |
| 4.4 | The frame is the wallpaper |
| 5.0 | The pattern blends into the exact wallpaper |

Every block is cut from the still at the rectangle `engine/kinds/logo.py` records, so the motion only moves the wallpaper's own pixels and adapts to any theme's colours and to Flexoki's smaller wordmark. The grid can't hold a few 2 px slivers of the wordmark, nor Flexoki's antialiased edges; the fade of the still over 4.0-4.4 s brings those in, when the blocks already sit exactly where the still has them.
