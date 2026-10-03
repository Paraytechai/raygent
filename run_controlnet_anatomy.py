import json
import urllib.request
import urllib.error
import time
import sys

def get_comfy_url():
    for port in [8189, 8188]:
        url = f"http://127.0.0.1:{port}"
        try:
            req = urllib.request.Request(f"{url}/system_stats")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return "http://127.0.0.1:8189"

def queue_prompt(prompt_workflow, host_url):
    payload = json.dumps({"prompt": prompt_workflow}).encode("utf-8")
    req = urllib.request.Request(f"{host_url}/prompt", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "node_errors" in data and data["node_errors"]:
                print(f"Node errors detected: {data['node_errors']}", file=sys.stderr)
                raise ValueError(f"Prompt validation failed: {data['node_errors']}")
            return data
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTPError: {e.code} - {err_msg}", file=sys.stderr)
        raise

def wait_for_completion(prompt_id, host_url, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{host_url}/history/{prompt_id}")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if prompt_id in data:
                    return data[prompt_id]
        except Exception as e:
            print(f"Polling error: {e}")
        time.sleep(2.0)
    raise TimeoutError(f"Workflow execution timed out after {timeout}s")

def build_workflow(host):
    # Check registered names from object_info
    req = urllib.request.Request(f"{host}/object_info/ControlNetLoader")
    with urllib.request.urlopen(req) as resp:
        info = json.loads(resp.read().decode("utf-8"))
        available_cn = info["ControlNetLoader"]["input"]["required"]["control_net_name"][0]
    
    openpose_model = None
    depth_model = None
    for m in available_cn:
        if "openpose" in m.lower():
            openpose_model = m
        if "depth" in m.lower():
            depth_model = m
            
    print(f"Using OpenPose model: {openpose_model}")
    print(f"Using Depth model: {depth_model}")
    
    wf = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
            }
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": "photorealistic full body portrait of athletic woman, natural studio lighting, high detail, realistic skin texture, beautiful face, natural anatomy, 8k masterpiece"
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": "bad anatomy, deformed limbs, extra fingers, mutated hands, backwards elbows, disconnected joints, plastic waxy skin, blurry, cartoon, 3d render"
            }
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": 1,
                "height": 768,
                "width": 512
            }
        },
        "5": {
            "class_type": "ControlNetLoader",
            "inputs": {
                "control_net_name": openpose_model
            }
        },
        "6": {
            "class_type": "ControlNetLoader",
            "inputs": {
                "control_net_name": depth_model
            }
        },
        "7": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "pose_reference.png"
            }
        },
        "13": {
            "class_type": "OpenposePreprocessor",
            "inputs": {
                "image": ["7", 0],
                "detect_hand": "enable",
                "detect_body": "enable",
                "detect_face": "enable",
                "resolution": 512,
                "scale_stick_for_xinsr_cn": "disable"
            }
        },
        "14": {
            "class_type": "MiDaS-DepthMapPreprocessor",
            "inputs": {
                "image": ["7", 0],
                "resolution": 512,
                "a": 6.28,
                "bg_threshold": 0.1
            }
        },
        "8": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["2", 0],
                "negative": ["3", 0],
                "control_net": ["5", 0],
                "image": ["13", 0],
                "strength": 0.48,
                "start_percent": 0.0,
                "end_percent": 0.85
            }
        },
        "9": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["8", 0],
                "negative": ["8", 1],
                "control_net": ["6", 0],
                "image": ["14", 0],
                "strength": 0.42,
                "start_percent": 0.0,
                "end_percent": 0.80
            }
        },
        "10": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": 6.5,
                "denoise": 1.0,
                "latent_image": ["4", 0],
                "model": ["1", 0],
                "positive": ["9", 0],
                "negative": ["9", 1],
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "seed": 888888,
                "steps": 25
            }
        },
        "11": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["10", 0],
                "vae": ["1", 2]
            }
        },
        "12": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "Realistic_Anatomy_DualStack",
                "images": ["11", 0]
            }
        },
        "15": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ControlNet_Pose_Skeleton",
                "images": ["13", 0]
            }
        },
        "16": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ControlNet_Depth_Map",
                "images": ["14", 0]
            }
        }
    }
    return wf

if __name__ == "__main__":
    host = get_comfy_url()
    print(f"Connected to ComfyUI at: {host}")
    
    wf = build_workflow(host)
    workflow_path = r"D:\Comfy-Desktop\ComfyUI-Shared\input\realistic_anatomy_controlnet_dual_stack.json"
    with open(workflow_path, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2)
    print(f"Updated workflow saved to {workflow_path}")
    
    print("Validating and submitting prompt to ComfyUI queue...")
    res = queue_prompt(wf, host)
    prompt_id = res.get("prompt_id")
    print(f"Workflow queued successfully! Prompt ID: {prompt_id}")
    
    print("Waiting for generation to complete...")
    hist = wait_for_completion(prompt_id, host, timeout=180)
    print("Workflow execution completed successfully!")
    
    outputs = hist.get("outputs", {})
    for node_id, out in outputs.items():
        if "images" in out:
            for img in out["images"]:
                print(f"[Node {node_id}] Generated: {img['filename']}")
