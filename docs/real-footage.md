# Paintings, photos and real footage

Scenes suit graphic wallpapers, where each shape can be lifted off a flat background and moved. Paintings and photos don't split that way: code can only reveal them, which reads as a slow fade rather than motion.

For those, start from a real video instead:

- **Image-to-video tools** that accept the wallpaper as the final frame, so the clip naturally settles on the picture.
- **Filmed or rendered footage** that ends on a shot matching the wallpaper.

Whatever the source, the result must meet the same pattern. `themotion check <video> <wallpaper>` tells you whether it does: it fails on a bright opening, a colour-matrix mismatch, or an ending that is not the exact wallpaper.

`themotion fit <video> <wallpaper>` re-finishes a footage intro's ending: it keeps every frame, blends the last 0.4 s into the wallpaper exactly as the check encodes it, holds it, and gives the settled frames the pattern's high quality. Use it when a video passes everything but the `end` check, which is common when the ending was blended into a copy of the wallpaper from a different decoder. Retiming and fading from black are still manual.
