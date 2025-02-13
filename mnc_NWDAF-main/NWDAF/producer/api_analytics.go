package producer

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os/exec"
	"time"

	"github.com/gin-gonic/gin"
)

// AnalyticsRequest represents the incoming analytics request
type AnalyticsRequest struct {
	AnalyticsID    string    `json:"analyticsId"`
	Target         string    `json:"target"`
	RequestingNfID string    `json:"requestingNfId"`
	TimeStamp      time.Time `json:"timestamp"`
}

type PredictionRequest struct {
	AnalyticsID    string `json:"analyticsId"`
	TargetUe       string `json:"TargetUe"`
	RequestingNfID string `json:"requestingNfId"`
	TargetTime     string `json:"TargetTime"`
}

func HandleAnalyticsRequest(c *gin.Context) { //, w http.ResponseWriter, r *http.Request) {
	// Set common headers
	c.Writer.Header().Set("Content-Type", "application/json")
	c.Writer.Header().Set("3gpp-Sbi-Message-Priority", "1")

	// Handle different HTTP methods
	switch c.Request.Method {
	case http.MethodPost:
		handleAnalyticsPost(c.Writer, c.Request)
	case http.MethodGet:
		handleAnalyticsGet(c.Writer, c.Request)
	default:
		http.Error(c.Writer, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
}

// AnalyticsResponse represents the analytics response
type AnalyticsResponse struct {
	AnalyticsID   string                 `json:"analyticsId"`
	Timestamp     time.Time              `json:"timestamp"`
	AnalyticsData map[string]interface{} `json:"analyticsData"`
	Status        string                 `json:"status"`
}

// func main() {
// 	// Create a new router
// 	http.HandleFunc("/nnwdaf-analyticsinfo/v1/analytics", handleAnalyticsRequest)

// 	// Start the server
// 	log.Printf("Starting NWDAF Analytics Info server on :8080")
// 	if err := http.ListenAndServe(":8080", nil); err != nil {
// 		log.Fatalf("Failed to start server: %v", err)
// 	}
// }

// func handleAnalyticsRequest(c *gin.Context, w http.ResponseWriter, r *http.Request) {
// 	// Set common headers
// 	w.Header().Set("Content-Type", "application/json")
// 	w.Header().Set("3gpp-Sbi-Message-Priority", "1")

// 	// Handle different HTTP methods
// 	switch r.Method {
// 	case http.MethodPost:
// 		handleAnalyticsPost(w, r)
// 	case http.MethodGet:
// 		handleAnalyticsGet(w, r)
// 	default:
// 		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
// 		return
// 	}
// }

func handleAnalyticsPost(w http.ResponseWriter, r *http.Request) {
	// Parse the request body
	var req AnalyticsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if req.AnalyticsID == "" || req.RequestingNfID == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	// Process analytics request (implement your analytics logic here)
	response := AnalyticsResponse{
		AnalyticsID: req.AnalyticsID,
		Timestamp:   time.Now(),
		AnalyticsData: map[string]interface{}{
			"result": "Sample analytics result",
			// Add your actual analytics data here
		},
		Status: "COMPLETED",
	}

	// Send response
	json.NewEncoder(w).Encode(response)
}

func (a *AnalyticsRequest) ToString() string {
	jsonBytes, err := json.Marshal(a)
	if err != nil {
		return ""
	}
	return string(jsonBytes)
}
func (a *PredictionRequest) ToString() string {
	jsonBytes, err := json.Marshal(a)
	if err != nil {
		return ""
	}
	return string(jsonBytes)
}

func handleAnalyticsGet(w http.ResponseWriter, r *http.Request) {
	// fmt.Fprintf(w, "Hello, you've reached the nwdaf's inference service!")

	var req PredictionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Get query parameters
	// analyticsID := r.URL.Query().Get("analytics-id")
	// if req.AnalyticsID == "" {
	// 	http.Error(w, "Missing analytics-id parameter", http.StatusBadRequest)
	// 	return
	// }

	pythonScript := "pythonmodule/main.py"

	// Create the command
	cmd := exec.Command("python3", pythonScript, req.ToString())

	// Capture the output
	// var out bytes.Buffer
	var out, errOut bytes.Buffer
	cmd.Stdout = &out
	// cmd.Stderr = &out
	cmd.Stderr = &errOut

	// Run the command
	err := cmd.Run()
	if err != nil {
		log.Fatalf("Error running Python script: %v\nError Output: %s", err, errOut.String())
	}

	// Print the output
	fmt.Println(out.String())

	// Process GET request (implement your analytics retrieval logic here)
	response := AnalyticsResponse{
		AnalyticsID: req.AnalyticsID,
		Timestamp:   time.Now(),
		AnalyticsData: map[string]interface{}{
			"result": fmt.Sprintf("Analytics data: %s", out.String()),
			// Add your actual analytics data here
		},
		Status: "COMPLETED",
	}

	// Send response
	json.NewEncoder(w).Encode(response)
}

// Middleware for validating 5G Core Network Function authentication
func authMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Check for required headers
		nfType := r.Header.Get("3gpp-Sbi-Calling-NF-Type")
		if nfType == "" {
			http.Error(w, "Missing NF type header", http.StatusUnauthorized)
			return
		}

		// Add your authentication logic here
		// Validate OAuth2 tokens, certificates, etc.

		next.ServeHTTP(w, r)
	}
}
