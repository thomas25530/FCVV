# 1. System dependencies
!apt update
!apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev build-essential

# 2. Install Python tools with pinned requests to satisfy Colab
!pip install --upgrade pip
# We pin requests==2.32.4 to keep Colab happy
!pip install "Cython<3.0" buildozer "requests==2.32.4" pyyaml certifi

!apt-get install -y autoconf automake libtool pkg-config

# 3. Extraction
!unzip -o projet_v15.zip

# 4. Java Config
import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

# 5. Build
# Note: If it still fails, go to Runtime -> Restart session and run from Step 3.
!buildozer android debug
