# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""
Sample new images from a pre-trained DiT.
"""
import torch
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
from torchvision.utils import save_image
from diffusion import create_diffusion
from diffusers.models import AutoencoderKL
from download import find_model
from models import DiT_models
import argparse
from tqdm import tqdm

def main(args):
    # Setup PyTorch:
    torch.manual_seed(args.seed)
    torch.set_grad_enabled(False)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if args.ckpt is None:
        assert args.model == "DiT-XL/2", "Only DiT-XL/2 models are available for auto-download."
        assert args.image_size in [256, 512]
        assert args.num_classes == 1000

    # Load model:
    latent_size = args.image_size // 8
    model = DiT_models[args.model](
        input_size=latent_size,
        num_classes=args.num_classes
    ).to(device)
    # Auto-download a pre-trained model or load a custom DiT checkpoint from train.py:
    ckpt_path = args.ckpt or f"DiT-XL-2-{args.image_size}x{args.image_size}.pt"
    state_dict = find_model(ckpt_path)
    model.load_state_dict(state_dict)
    model.eval()  # important!
    diffusion = create_diffusion(str(args.num_sampling_steps))
    vae = AutoencoderKL.from_pretrained(f"stabilityai/sd-vae-ft-{args.vae}").to(device)

    # Labels to condition the model with (feel free to change):
    class_labels = [207, 360, 387, 974, 88, 979, 417, 279]
    t_c = args.tc

    if args.classes is not None:
        class_labels = args.classes

    if args.all_classes is True:
        class_labels = [i for i in range(1000)]

    if args.n_samples > 1:
        for i in tqdm(range(args.n_samples)):
            n = len(class_labels)
            if t_c is not None:
                assert n == len(t_c)


            z = torch.randn(n, 4, latent_size, latent_size, device=device)
            y = torch.tensor(class_labels, device=device)

            # Setup classifier-free guidance:
            z = torch.cat([z, z], 0)
            y_null = torch.tensor([1000] * n, device=device)
            y = torch.cat([y, y_null], 0)
            model_kwargs = dict(y=y, t_c = t_c,cfg_scale=args.cfg_scale)


            # Sample images:
            samples = diffusion.p_sample_loop(
        model.forward_with_cfg, z.shape, z, clip_denoised=False, model_kwargs=model_kwargs, progress=True, device=device,t_start = args.t_start, t_c= args.t_c
    )
            samples, _ = samples.chunk(2, dim=0)  # Remove null class samples
            samples = vae.decode(samples / 0.18215).sample

            torch.save(samples.cpu(),f"{args.save_dir}/{i}_latents.pt")

        
            if samples.size(0) > 5:
                for j in range(0,samples.size(0),5):
                    if j+5 < samples.size(0):
                       samples_2 = vae.decode(samples[j:j+5,:,:,:] / 0.18215).sample
                    else:
                        samples_2 = vae.decode(samples[j:samples.size(0),:,:,:] / 0.18215).sample
                    for k in range(samples_2.size(0)):
                        save_image(samples_2[k, :, :, :], f'{args.save_dir}/{i}_{j*5+k}.png',normalize=True,value_range=(-1,1))
            else:
             samples = vae.decode(samples / 0.18215).sample


            for j in range(samples.size(0)):
               save_image(samples[i, :, :, :], f'{args.save_dir}/{i}_{j}.png',normalize=True,value_range=(-1,1))


    else:
        
        # Create sampling noise:
        n = len(class_labels)
        z = torch.randn(n, 4, latent_size, latent_size, device=device)
        y = torch.tensor(class_labels, device=device)

        if t_c is not None:
            assert len(args.tc) == n



        # Setup classifier-free guidance:
        z = torch.cat([z, z], 0)
        y_null = torch.tensor([1000] * n, device=device)
        y = torch.cat([y, y_null], 0)
        model_kwargs = dict(y=y, t_c =args.t_c, cfg_scale=args.cfg_scale)

        # Sample images:
        samples = diffusion.p_sample_loop(
        model.forward_with_cfg, z.shape, z, clip_denoised=False, model_kwargs=model_kwargs, progress=True, device=device,t_start = args.t_start, t_c= args.tc
    )
        samples, _ = samples.chunk(2, dim=0)  # Remove null class samples


                

      






                        


            





                  

              

                   


    

            
        



    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, choices=list(DiT_models.keys()), default="DiT-XL/2")
    parser.add_argument("--vae", type=str, choices=["ema", "mse"], default="mse")
    parser.add_argument("--image-size", type=int, choices=[256, 512], default=256)
    parser.add_argument("--num-classes", type=int, default=1000)
    parser.add_argument("--cfg-scale", type=float, default=4.0)
    parser.add_argument("--num-sampling-steps", type=int, default=250)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ckpt", type=str, default=None,
                        help="Optional path to a DiT checkpoint (default: auto-download a pre-trained DiT-XL/2 model).")
    parser.add_argument("--t-start", type=int, default = None)
    parser.add_argument("--tc", '--list', nargs='+', default = None, help = "class smallest merger times")
    parser.add_argument('--classes','--list', nargs='+', default = None, help = "class list")
    parser.add_argument("--all-classes",type=bool, default=False)
    parser.add_argument("--n-samples", type=int, default = 1)
    parser.add_argument("--save-dir",type=str,default=None)

    args = parser.parse_args()
    main(args)
