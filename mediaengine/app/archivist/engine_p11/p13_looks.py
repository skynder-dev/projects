"""Colour looks of a reel: FFmpeg filters for the joined picture (8-bit yuv420p in TV levels, as the reel's single
encode has it). One source for the engine's final encode ("look" in --dress) and the app's small preview pictures.

"As filmed" (natural) has no filter. Tuned on drone, landscape and portrait pictures (2026-10-27); every look keeps the
picture in TV levels:
- vivid: brighter middle tones and a soft S-curve (no clipped whites or blacks), richer colours;
- warm: a golden white balance;
- film: lifted blacks, soft highlights, cool shadows and warm lights, a little less colour (in RGB through exact
  lookup tables: about a third more time for the final encode).
"""
_X = "clip((val-16)/219,0,1)"          # luma 16..235 as 0..1

LOOKS = {
    "vivid": f"lutyuv=y='clip(16+219*pow({_X}+0.35*{_X}*(1-{_X})*(2*{_X}-1),0.93),16,235)',eq=saturation=1.3",
    "warm": "lutyuv=u='clip(128+(val-128)*1.06-6,16,240)':v='clip(128+(val-128)*1.06+5,16,240)'",
    "film": ("scale=in_range=tv:in_color_matrix=bt709:out_range=pc,format=rgb24,"
             "curves=r='0/0.04 0.5/0.53 1/0.98':g='0/0.03 0.5/0.51 1/0.97':b='0/0.07 0.5/0.49 1/0.93':all='0/0 0.3/0.26 0.7/0.75 1/1',"
             "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p,eq=saturation=0.88"),
}
