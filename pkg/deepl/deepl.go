package deepl

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

type Client struct {
	apiKey string
}

func NewClient(apiKey string) *Client {
	return &Client{apiKey: apiKey}
}

type DeepLResponse struct {
	Translations []struct {
		Text string `json:"text"`
	} `json:"translations"`
}

var langMap = map[string]string{
	"zh": "ZH", "vi": "VI", "en": "EN", "ja": "JA",
	"ko": "KO", "th": "TH", "id": "ID", "ms": "MS",
	"fr": "FR", "de": "DE", "es": "ES", "pt": "PT",
	"ru": "RU", "it": "IT", "nl": "NL", "pl": "PL",
	"ar": "AR", "tr": "TR", "cs": "CS", "da": "DA",
	"el": "EL", "fi": "FI", "hu": "HU", "sv": "SV",
	"uk": "UK", "ro": "RO", "sk": "SK",
}

func (c *Client) Translate(text, targetLang string) (string, error) {
	if c.apiKey == "" {
		return "", fmt.Errorf("DeepL API key is not configured")
	}

	target, ok := langMap[targetLang]
	if !ok {
		return "", fmt.Errorf("unsupported DeepL target language: %s", targetLang)
	}

	apiURL := "https://api-free.deepl.com/v2/translate"

	form := url.Values{}
	form.Set("text", text)
	form.Set("target_lang", target)

	req, err := http.NewRequest("POST", apiURL, strings.NewReader(form.Encode()))
	if err != nil {
		return "", fmt.Errorf("deepl create request error: %w", err)
	}

	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Authorization", "DeepL-Auth-Key "+c.apiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("deepl http error: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("deepl error status %d: %s", resp.StatusCode, string(body))
	}

	var result DeepLResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("deepl parse response error: %w", err)
	}

	if len(result.Translations) == 0 {
		return "", fmt.Errorf("deepl empty translation result")
	}

	return result.Translations[0].Text, nil
}