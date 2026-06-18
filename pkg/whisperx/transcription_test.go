package whisperx

import "testing"

func TestWithPythonUTF8EnvAddsMissingVariables(t *testing.T) {
	env := withPythonUTF8Env([]string{"PATH=/usr/bin"})
	assertEnvValue(t, env, "PYTHONUTF8=1")
	assertEnvValue(t, env, "PYTHONIOENCODING=utf-8")
}

func TestWithPythonUTF8EnvOverridesExistingVariables(t *testing.T) {
	env := withPythonUTF8Env([]string{
		"PYTHONUTF8=0",
		"PYTHONIOENCODING=cp1252",
	})
	assertEnvValue(t, env, "PYTHONUTF8=1")
	assertEnvValue(t, env, "PYTHONIOENCODING=utf-8")
}

func assertEnvValue(t *testing.T, env []string, want string) {
	t.Helper()
	count := 0
	for _, v := range env {
		if v == want {
			count++
		}
	}
	if count != 1 {
		t.Fatalf("%s count = %d, want 1 in %#v", want, count, env)
	}
}
