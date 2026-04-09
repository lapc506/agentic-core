package remote

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sync"
	"time"
)

type ConnectionState string

const (
	Connected    ConnectionState = "connected"
	Connecting   ConnectionState = "connecting"
	Reconnecting ConnectionState = "reconnecting"
	Disconnected ConnectionState = "disconnected"
)

type RemoteInstance struct {
	ID         string          `json:"id"`
	Name       string          `json:"name"`
	URL        string          `json:"url"`
	State      ConnectionState `json:"state"`
	Agent      string          `json:"agent,omitempty"`
	Model      string          `json:"model,omitempty"`
	LastSeen   time.Time       `json:"last_seen"`
	Retries    int             `json:"retries"`
	MaxRetries int             `json:"max_retries"`
}

type RemoteManager struct {
	mu        sync.RWMutex
	instances map[string]*RemoteInstance
	token     string
}

func NewRemoteManager(token string) *RemoteManager {
	return &RemoteManager{
		instances: make(map[string]*RemoteInstance),
		token:     token,
	}
}

func (rm *RemoteManager) Add(id, name, url string) *RemoteInstance {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	inst := &RemoteInstance{
		ID: id, Name: name, URL: url,
		State: Disconnected, MaxRetries: 10,
	}
	rm.instances[id] = inst
	return inst
}

func (rm *RemoteManager) Remove(id string) {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	delete(rm.instances, id)
}

func (rm *RemoteManager) Get(id string) *RemoteInstance {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	return rm.instances[id]
}

func (rm *RemoteManager) List() []*RemoteInstance {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	list := make([]*RemoteInstance, 0, len(rm.instances))
	for _, inst := range rm.instances {
		list = append(list, inst)
	}
	return list
}

func (rm *RemoteManager) UpdateState(id string, state ConnectionState) {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	if inst, ok := rm.instances[id]; ok {
		inst.State = state
		if state == Connected {
			inst.LastSeen = time.Now()
			inst.Retries = 0
		}
	}
}

func (rm *RemoteManager) ValidateToken(token string) bool {
	mac := hmac.New(sha256.New, []byte(rm.token))
	mac.Write([]byte("agentic-studio"))
	expected := hex.EncodeToString(mac.Sum(nil))
	return hmac.Equal([]byte(token), []byte(expected))
}

func (rm *RemoteManager) GenerateSessionToken() string {
	mac := hmac.New(sha256.New, []byte(rm.token))
	mac.Write([]byte(fmt.Sprintf("session-%d", time.Now().UnixNano())))
	return hex.EncodeToString(mac.Sum(nil))
}

func (rm *RemoteManager) Count() int {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	return len(rm.instances)
}
