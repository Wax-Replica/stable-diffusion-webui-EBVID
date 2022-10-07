"""
    *******
    Stable Diffusion / EBsynth hacky video script by @ Wax Replica
    
    For use with Automatic1111's webui (https://github.com/AUTOMATIC1111/stable-diffusion-webui) - place this in the scripts folder
    
    Need to download ebsynth binary from https://github.com/jamriska/ebsynth - scroll down a bit in the readme. put it somewhere convenient and enter the path on the ui

    takes a folder of images as input, outputs to another folder - ive been using ezgif.com to turn them into gifs
    
    the progress bar is broken and i dont really care to fix it
    
    mess around some with the settings, use more steps than you think you need.

    *******
"""

import modules.scripts as scripts
import gradio as gr
import os
import shutil
from PIL import Image, ImageOps, ImageChops

from modules.processing import process_images, Processed
from modules.shared import opts, cmd_opts, state


class Script(scripts.Script):

    def title(self):
        return "EBVID"

    def ui(self, is_img2img):
        synthpath = gr.Textbox(label="Path of ebsynth executable")
        
        dirsrc = gr.Textbox(label="Input directory")
        dirsynth = gr.Textbox(label="Temp files directory (SHOULD BE EMPTY)")
        dirout = gr.Textbox(label="Output directory (SHOULD BE EMPTY)")
        
        icfg_scale = gr.Slider(minimum=0.0, maximum=15.0, step=0.5, label='Past Frame 1 CFG Scale', value=7.0)
        isteps = gr.Slider(minimum=1, maximum=150, step=1, label="Past Frame 1 Sampling Steps", value=50)
        idenoising_strength = gr.Slider(minimum=0.0, maximum=1.0, step=0.01, label='Past Frame 1 Denoising strength', value=0.4)
        
        refreq = gr.Number(value = 5, label="run through stableD and update ebsynth guides every x frames", interactive = True, precision = 0)
        
        stopby = gr.Number(value=0, label="Stopby: Do only this many frames, for testing. 0 to do all", interactive = True, precision = 0)
        
        compound = gr.Slider(value = 0.5, maximum = 1.0, minimum = 0.0, label="blend source image for stable D steps, 0 = original frame, 1 = ebsynth output")
        
        return [synthpath, dirsrc, dirsynth, dirout, icfg_scale, isteps, idenoising_strength, refreq, stopby, compound]

    def show(self, is_img2img):
        return is_img2img

    def run(self, p, synthpath, dirsrc, dirsynth, dirout, icfg_scale, isteps, idenoising_strength, refreq, stopby, compound):
    
        srcframes = [file for file in [os.path.join(dirsrc, x) for x in os.listdir(dirsrc)] if os.path.isfile(file)]
        
        p.n_iter = 1
        p.batch_size = 1
        
        if stopby != 0:
            srcframes = srcframes[0:stopby]
        
        print (len(srcframes), "frames to process")

        p.do_not_save_grid = True
        p.do_not_save_samples = True

        state.job_count = len(srcframes)
        
        for x, srcframe in enumerate(srcframes):
            state.job = f"{x+1} out of {len(srcframes)}"

            if state.interrupted:
                break
            scaleframe = os.path.join(dirsynth, f"scale{x}.png")
            img = Image.open(srcframe)
            img = img.resize((p.width, p.height))
            img.save(scaleframe)
            
            if x == 0:
                
                lastguide = scaleframe
                p.init_images = [img]
                proc = process_images(p)
                
                p.cfg_scale = icfg_scale
                p.steps = isteps
                p.denoising_strength = idenoising_strength
                filename = f"{x}.png"
                laststyle = os.path.join(dirout, filename)
                for n, processed_image in enumerate(proc.images):
                    processed_image.save(laststyle)
            else:
                ebpath = os.path.join(dirsynth, f"{x}.png")
                ebcmd = f'cmd /c "{synthpath} -style {laststyle} -guide {lastguide} {scaleframe} -output {ebpath}'
                print(ebcmd)
                os.system(ebcmd)
                filename = f"{x}.png"
                outpath = os.path.join(dirout, filename)
                if x % refreq == 0:
                    laststyle = outpath
                    lastguide = scaleframe
                    imge = Image.open(ebpath)
                    imgs = Image.open(scaleframe)
                    imge = imge.convert("RGB")
                    imgs = imgs.convert("RGB")
                    img = Image.blend(imgs,imge,compound)
                    p.init_images = [img]
                    print(f"running stableD on {p.init_images}")
                    proc = process_images(p)
                    for n, processed_image in enumerate(proc.images):
                        processed_image.save(outpath)
                else:
                    shutil.copyfile(ebpath, outpath)

                