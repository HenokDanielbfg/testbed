// main.go

package main

import (
    "bytes"
    "fmt"
    "log"
    "os/exec"
)

func main() {
    // Specify the Python script and the argument
    pythonScript := "script.py"
    name := "Alice"

    // Create the command
    cmd := exec.Command("python3", pythonScript, name)

    // Capture the output
    var out bytes.Buffer
    cmd.Stdout = &out
    cmd.Stderr = &out

    // Run the command
    err := cmd.Run()
    if err != nil {
        log.Fatalf("Error running Python script: %v", err)
    }

    // Print the output
    fmt.Println(out.String())
}

