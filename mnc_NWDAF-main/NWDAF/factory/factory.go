/*
 * NWDAF Configuration Factory
 */

package factory

import (
	"fmt"
	"strings"

	// "io/ioutil"
	"os"

	"gopkg.in/yaml.v2"

	"nwdaf.com/logger"
)

var NwdafConfig *Config

// Load only the uncommented event types from YAML
func LoadSubscriptionConfig(filename string) (*SubscriptionConfig, error) {
	config := &SubscriptionConfig{}

	// Read file as a raw string (to handle comments)
	rawContent, err := os.ReadFile(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to read subscription config: %v", err)
	}

	// Remove commented-out lines (lines starting with #)
	filteredContent := ""
	lines := strings.Split(string(rawContent), "\n")
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if !strings.HasPrefix(trimmed, "#") {
			filteredContent += line + "\n"
		}
	}

	// Parse YAML
	if err := yaml.Unmarshal([]byte(filteredContent), config); err != nil {
		return nil, fmt.Errorf("failed to parse subscription config: %v", err)
	}
	return config, nil
}

func InitConfigFactory(f string, cfg *Config) error {
	if f == "" {
		// Use default config path
		f = NwdafDefaultConfigPath
	}

	if content, err := os.ReadFile(f); err != nil {
		return fmt.Errorf("[Factory] %+v", err)
	} else {
		logger.CfgLog.Infof("Read config from [%s]", f)
		if yamlErr := yaml.Unmarshal(content, cfg); yamlErr != nil {
			return fmt.Errorf("[Factory] %+v", yamlErr)
		}
	}

	return nil
}

func ReadConfig(cfgPath string) (*Config, error) {
	cfg := &Config{}
	if err := InitConfigFactory(cfgPath, cfg); err != nil {
		return nil, fmt.Errorf("ReadConfig [%s] Error: %+v", cfgPath, err)
	}
	// if _, err := cfg.Validate(); err != nil {
	// 	validErrs := err.(govalidator.Errors).Errors()
	// 	for _, validErr := range validErrs {
	// 		logger.CfgLog.Errorf("%+v", validErr)
	// 	}
	// 	logger.CfgLog.Errorf("[-- PLEASE REFER TO SAMPLE CONFIG FILE COMMENTS --]")
	// 	return nil, fmt.Errorf("Config validate Error")
	// }

	return cfg, nil
}

func CheckConfigVersion() error {
	currentVersion := NwdafConfig.GetVersion()

	if currentVersion != NWDAF_EXPECTED_CONFIG_VERSION {
		return fmt.Errorf("config version is [%s], but expected is [%s].",
			currentVersion, NWDAF_EXPECTED_CONFIG_VERSION)
	}

	logger.CfgLog.Infof("config version [%s]", currentVersion)

	return nil
}
