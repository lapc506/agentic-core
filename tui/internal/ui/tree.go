package ui

import (
	"fmt"
	"strings"
)

// TreeNode represents a single node in the agent execution tree.
type TreeNode struct {
	ID       string
	Label    string
	Status   string // running, completed, failed, or empty for pending
	Children []*TreeNode
	Expanded bool
}

// RenderTree recursively renders a TreeNode and its children as a Unicode tree.
// prefix is the leading whitespace/connector characters for the current depth.
// isLast indicates whether this node is the last child of its parent.
func RenderTree(node *TreeNode, prefix string, isLast bool) string {
	var sb strings.Builder

	connector := "├── "
	if isLast {
		connector = "└── "
	}

	statusIcon := "○"
	statusStyle := StyleDim
	switch node.Status {
	case "running":
		statusIcon = "◐"
		statusStyle = StyleTitle
	case "completed":
		statusIcon = "●"
		statusStyle = StyleStatus
	case "failed":
		statusIcon = "✕"
		statusStyle = StyleError
	}

	sb.WriteString(fmt.Sprintf("%s%s%s\n",
		StyleDim.Render(prefix+connector),
		statusStyle.Render(statusIcon+" "+node.Label),
		StyleDim.Render(fmt.Sprintf(" [%s]", node.ID)),
	))

	if node.Expanded {
		childPrefix := prefix
		if isLast {
			childPrefix += "    "
		} else {
			childPrefix += "│   "
		}
		for i, child := range node.Children {
			sb.WriteString(RenderTree(child, childPrefix, i == len(node.Children)-1))
		}
	}

	return sb.String()
}
