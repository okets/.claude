#!/usr/bin/env python3
"""
Voice Manager for smarter-claude TTS System

Handles automatic installation, validation, and management of TTS voices.
"""

import subprocess
import sys
import os
import platform
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class VoiceManager:
    def __init__(self):
        self.system = platform.system()
        self.claude_dir = Path.home() / ".claude" / ".claude" / "smarter-claude"
        self.settings_file = self.claude_dir / "smarter-claude.json"
        
        # Voice engine definitions
        self.voice_engines = {
            # Kokoro TTS voices (high-quality neural)
            "kokoro-af_alloy": {
                "name": "Kokoro Alloy (American Female)",
                "dependencies": ["kokoro-onnx"],
                "requires_uv": True,
                "platform_support": ["Darwin", "Linux", "Windows"],
                "test_command": ["uv", "run", "kokoro_voice.py", "kokoro-af_alloy", "test"]
            },
            "kokoro-af_nicole": {
                "name": "Kokoro Nicole (American Female, Whispering)",
                "dependencies": ["kokoro-onnx"],
                "requires_uv": True,
                "platform_support": ["Darwin", "Linux", "Windows"],
                "test_command": ["uv", "run", "kokoro_voice.py", "kokoro-af_nicole", "test"]
            },
            "kokoro-am_puck": {
                "name": "Kokoro Puck (American Male)",
                "dependencies": ["kokoro-onnx"],
                "requires_uv": True,
                "platform_support": ["Darwin", "Linux", "Windows"],
                "test_command": ["uv", "run", "kokoro_voice.py", "kokoro-am_puck", "test"]
            },
            # System voices
            "macos-female": {
                "name": "macOS female voice (Samantha)",
                "dependencies": [],
                "requires_uv": False,
                "platform_support": ["Darwin"],
                "test_command": ["say", "-v", "Samantha", "test"]
            },
            "macos-male": {
                "name": "macOS male voice (Alex)",
                "dependencies": [],
                "requires_uv": False,
                "platform_support": ["Darwin"],
                "test_command": ["say", "-v", "Alex", "test"]
            },
        }

    def check_uv_installed(self) -> bool:
        """Check if UV package manager is installed."""
        try:
            result = subprocess.run(["uv", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def install_uv(self) -> bool:
        """Install UV package manager if not present."""
        print("📦 Installing UV package manager...")
        try:
            if self.system == "Darwin":
                # Use Homebrew on macOS
                result = subprocess.run(["brew", "install", "uv"], 
                                      capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    print("✅ UV installed successfully via Homebrew")
                    return True
                
                # Fallback to curl installer
                print("🔄 Trying curl installer...")
                result = subprocess.run([
                    "curl", "-LsSf", "https://astral.sh/uv/install.sh"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    install_script = result.stdout
                    result = subprocess.run(["sh", "-c", install_script], 
                                          capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        print("✅ UV installed successfully via curl")
                        return True
                        
            else:  # Linux
                result = subprocess.run([
                    "curl", "-LsSf", "https://astral.sh/uv/install.sh", "|", "sh"
                ], shell=True, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print("✅ UV installed successfully")
                    return True
                    
        except Exception as e:
            print(f"❌ Failed to install UV: {e}")
            
        return False

    def install_ffmpeg(self) -> bool:
        """Install ffmpeg for audio processing."""
        print("🎵 Installing ffmpeg...")
        try:
            if self.system == "Darwin":
                result = subprocess.run(["brew", "install", "ffmpeg"], 
                                      capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    print("✅ ffmpeg installed successfully")
                    return True
            elif self.system == "Linux":
                # Try apt-get first
                result = subprocess.run(["sudo", "apt-get", "update"], 
                                      capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    result = subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], 
                                          capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        print("✅ ffmpeg installed successfully")
                        return True
        except Exception as e:
            print(f"❌ Failed to install ffmpeg: {e}")
            
        return False

    def install_kokoro_tts(self) -> bool:
        """Install Kokoro TTS via UV."""
        if not self.check_uv_installed():
            if not self.install_uv():
                return False
                
        print("🗣️  Installing Kokoro TTS...")
        try:
            # Install kokoro-onnx package
            result = subprocess.run(["uv", "add", "kokoro-onnx"], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print("✅ Kokoro TTS installed successfully")
                return True
            else:
                print(f"❌ Kokoro TTS installation failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Failed to install Kokoro TTS: {e}")
            return False

    def test_voice_engine(self, engine: str) -> bool:
        """Test if a voice engine is working properly."""
        if engine not in self.voice_engines:
            return False
            
        engine_info = self.voice_engines[engine]
        
        # Check platform support
        if self.system not in engine_info["platform_support"]:
            return False
            
        # Run test command
        try:
            test_cmd = engine_info["test_command"]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def install_voice_engine(self, engine: str) -> bool:
        """Install a specific voice engine and its dependencies."""
        if engine not in self.voice_engines:
            print(f"❌ Unknown voice engine: {engine}")
            return False
            
        engine_info = self.voice_engines[engine]
        
        # Check platform support
        if self.system not in engine_info["platform_support"]:
            print(f"❌ {engine} is not supported on {self.system}")
            return False
            
        print(f"🔧 Installing {engine_info['name']}...")
        
        # Install dependencies
        if "kokoro-onnx" in engine_info["dependencies"]:
            if not self.install_kokoro_tts():
                return False
                
        if "ffmpeg" in engine_info["dependencies"]:
            if not self.install_ffmpeg():
                return False
                
                
        # Test the installation
        if self.test_voice_engine(engine):
            print(f"✅ {engine_info['name']} installed and tested successfully")
            return True
        else:
            print(f"❌ {engine_info['name']} installation failed validation")
            return False

    def get_voice_status(self) -> Dict[str, Dict[str, any]]:
        """Get installation status of all voice engines."""
        status = {}
        for engine, info in self.voice_engines.items():
            is_supported = self.system in info["platform_support"]
            is_installed = self.test_voice_engine(engine) if is_supported else False
            
            status[engine] = {
                "name": info["name"],
                "supported": is_supported,
                "installed": is_installed,
                "dependencies": info["dependencies"]
            }
            
        return status

    def install_all_supported_voices(self) -> Dict[str, bool]:
        """Install all voice engines supported on current platform."""
        results = {}
        status = self.get_voice_status()
        
        for engine, info in status.items():
            if info["supported"] and not info["installed"]:
                print(f"\n📥 Installing {engine}...")
                results[engine] = self.install_voice_engine(engine)
            elif info["installed"]:
                print(f"✅ {engine} already installed")
                results[engine] = True
            else:
                print(f"⏭️  Skipping {engine} (not supported on {self.system})")
                results[engine] = False
                
        return results

    def get_recommended_voice(self) -> Optional[str]:
        """Get recommended voice engine for current platform."""
        status = self.get_voice_status()
        
        # Priority order for recommendations
        priority = ["kokoro-am_puck", "kokoro-af_alloy", "kokoro-af_nicole", "macos-female", "macos-male"]
        
        for engine in priority:
            if engine in status and status[engine]["supported"] and status[engine]["installed"]:
                return engine
                
        return None

    def demo_voice(self, engine: str, text: str = "Hello, this is a test of the TTS system.") -> bool:
        """Demo a voice engine with sample text."""
        if not self.test_voice_engine(engine):
            print(f"❌ {engine} is not available")
            return False
            
        print(f"🔊 Testing {engine}...")
        
        if engine.startswith("macos-"):
            voice = "Samantha" if "female" in engine else "Alex"
            try:
                subprocess.run(["say", "-v", voice, text], timeout=10)
                return True
            except Exception as e:
                print(f"❌ Demo failed: {e}")
                return False
        else:
            print(f"ℹ️  {engine} demo requires TTS script execution")
            return True


def main():
    """Main CLI interface for voice manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage smarter-claude TTS voices")
    parser.add_argument("command", choices=["status", "install", "install-all", "test", "demo", "recommend"],
                       help="Command to execute")
    parser.add_argument("--engine", help="Specific voice engine (for install, test, demo)")
    parser.add_argument("--text", default="Hello, this is a test of the TTS system.",
                       help="Text for demo (default: sample text)")
    
    args = parser.parse_args()
    
    vm = VoiceManager()
    
    if args.command == "status":
        print("🎤 Voice Engine Status:\n")
        status = vm.get_voice_status()
        for engine, info in status.items():
            support_icon = "✅" if info["supported"] else "❌"
            install_icon = "✅" if info["installed"] else "❌"
            print(f"{engine:15} | {support_icon} Supported | {install_icon} Installed | {info['name']}")
            
    elif args.command == "install":
        if not args.engine:
            print("❌ Please specify --engine for install command")
            sys.exit(1)
        success = vm.install_voice_engine(args.engine)
        sys.exit(0 if success else 1)
        
    elif args.command == "install-all":
        print("🚀 Installing all supported voice engines...\n")
        results = vm.install_all_supported_voices()
        success_count = sum(1 for r in results.values() if r)
        total_count = len([r for r in results.values() if r is not False])
        print(f"\n📊 Installation complete: {success_count}/{total_count} engines installed")
        
    elif args.command == "test":
        if not args.engine:
            print("❌ Please specify --engine for test command")
            sys.exit(1)
        success = vm.test_voice_engine(args.engine)
        print(f"{'✅' if success else '❌'} {args.engine} test {'passed' if success else 'failed'}")
        sys.exit(0 if success else 1)
        
    elif args.command == "demo":
        if not args.engine:
            print("❌ Please specify --engine for demo command")
            sys.exit(1)
        success = vm.demo_voice(args.engine, args.text)
        sys.exit(0 if success else 1)
        
    elif args.command == "recommend":
        recommended = vm.get_recommended_voice()
        if recommended:
            print(f"🎯 Recommended voice engine: {recommended}")
            print(f"📝 {vm.voice_engines[recommended]['name']}")
        else:
            print("❌ No suitable voice engines found. Run 'install-all' first.")


if __name__ == "__main__":
    main()