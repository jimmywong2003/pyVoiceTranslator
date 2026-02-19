"""
Streaming UI - Phase 1.4

UI components for displaying streaming translation with:
- Draft mode: Grey italic text (unstable)
- Final mode: Black bold text (stable)
- Diff visualization: Highlight changes between drafts
- Stability indicators: Show text confidence
- Smooth transitions: Fade between states
"""

import time
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class DisplayState:
    """Current display state."""
    text: str
    is_final: bool
    stability: float
    timestamp: float


class DiffVisualizer:
    """
    Visualizes differences between text versions.
    
    Phase 1.4: Highlights changes for smooth UI transitions.
    """
    
    @staticmethod
    def compute_diff(old_text: str, new_text: str) -> List[Tuple[str, str]]:
        """
        Compute word-level diff between old and new text.
        
        Returns:
            List of (word, status) tuples where status is:
            - 'same': Unchanged word
            - 'added': New word
            - 'removed': Removed word
        """
        old_words = old_text.split()
        new_words = new_text.split()
        
        matcher = SequenceMatcher(None, old_words, new_words)
        result = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Unchanged words
                for word in old_words[i1:i2]:
                    result.append((word, 'same'))
            elif tag == 'delete':
                # Removed words
                for word in old_words[i1:i2]:
                    result.append((word, 'removed'))
            elif tag == 'insert':
                # Added words
                for word in new_words[j1:j2]:
                    result.append((word, 'added'))
            elif tag == 'replace':
                # Replaced words (remove old, add new)
                for word in old_words[i1:i2]:
                    result.append((word, 'removed'))
                for word in new_words[j1:j2]:
                    result.append((word, 'added'))
        
        return result
    
    @staticmethod
    def format_diff(diff: List[Tuple[str, str]], 
                    highlight_added: bool = True) -> str:
        """
        Format diff as HTML-like string with markers.
        
        Args:
            diff: List of (word, status) tuples
            highlight_added: Whether to highlight added words
            
        Returns:
            Formatted text with change markers
        """
        parts = []
        
        for word, status in diff:
            if status == 'same':
                parts.append(word)
            elif status == 'added':
                if highlight_added:
                    # Mark added words with special marker
                    parts.append(f"[[ADD:{word}]]")
                else:
                    parts.append(word)
            elif status == 'removed':
                # Skip removed words in display
                pass
        
        return ' '.join(parts)
    
    @staticmethod
    def get_change_summary(diff: List[Tuple[str, str]]) -> dict:
        """Get summary of changes."""
        added = sum(1 for _, s in diff if s == 'added')
        removed = sum(1 for _, s in diff if s == 'removed')
        same = sum(1 for _, s in diff if s == 'same')
        
        total_old = removed + same
        total_new = added + same
        
        return {
            'added': added,
            'removed': removed,
            'same': same,
            'total_old': total_old,
            'total_new': total_new,
            'change_ratio': (added + removed) / max(total_old, 1),
        }


class StreamingUI:
    """
    Streaming UI with diff-based transitions.
    
    Phase 1.4: Smooth transitions between draft and final states.
    
    Features:
    - Draft display: Grey italic (unstable)
    - Final display: Black bold (stable)
    - Diff highlighting: Show what changed
    - Stability indicators: Visual confidence
    - Smooth transitions: Fade effects
    
    Usage:
        ui = StreamingUI()
        
        # Show draft
        ui.show_draft("Hello...", stability=0.6)
        
        # Update draft
        ui.update_draft("Hello world...", stability=0.8)
        
        # Show final
        ui.show_final("Hello world today.", stability=1.0)
    """
    
    # Stability thresholds for visual indicators
    STABILITY_LOW = 0.5
    STABILITY_MEDIUM = 0.8
    
    def __init__(self):
        """Initialize streaming UI."""
        self._current_state: Optional[DisplayState] = None
        self._previous_state: Optional[DisplayState] = None
        self._diff_visualizer = DiffVisualizer()
        
        # Statistics
        self._draft_updates = 0
        self._final_shows = 0
        self._total_transitions = 0
        
        logger.info("StreamingUI initialized (Phase 1.4)")
    
    def show_draft(self, text: str, stability: float = 0.0):
        """
        Show draft text (unstable, grey italic).
        
        Args:
            text: Draft text to display
            stability: Stability score (0.0-1.0)
        """
        self._previous_state = self._current_state
        self._current_state = DisplayState(
            text=text,
            is_final=False,
            stability=stability,
            timestamp=time.time()
        )
        
        self._draft_updates += 1
        
        # Get stability indicator
        indicator = self._get_stability_indicator(stability)
        
        logger.debug(f"Draft: '{text[:40]}...' (stability: {stability:.2f})")
        
        # Return display format (can be used by actual UI framework)
        return {
            'text': text,
            'style': 'draft',
            'color': 'grey',
            'font_style': 'italic',
            'stability_indicator': indicator,
            'opacity': self._get_stability_opacity(stability),
        }
    
    def update_draft(self, new_text: str, stability: float = 0.0) -> dict:
        """
        Update draft with diff highlighting.
        
        Shows what changed from previous draft.
        
        Args:
            new_text: New draft text
            stability: Stability score
            
        Returns:
            Display format with diff information
        """
        old_text = self._current_state.text if self._current_state else ""
        
        # Compute diff
        diff = self._diff_visualizer.compute_diff(old_text, new_text)
        change_summary = self._diff_visualizer.get_change_summary(diff)
        
        # Update state
        self._previous_state = self._current_state
        self._current_state = DisplayState(
            text=new_text,
            is_final=False,
            stability=stability,
            timestamp=time.time()
        )
        
        self._draft_updates += 1
        self._total_transitions += 1
        
        # Determine if significant change
        is_significant = change_summary['change_ratio'] > 0.3
        
        logger.debug(
            f"Draft update: '{new_text[:40]}...' "
            f"(+{change_summary['added']}/-{change_summary['removed']}, "
            f"stability: {stability:.2f})"
        )
        
        return {
            'text': new_text,
            'style': 'draft_update',
            'color': 'grey',
            'font_style': 'italic',
            'stability_indicator': self._get_stability_indicator(stability),
            'opacity': self._get_stability_opacity(stability),
            'diff': diff,
            'change_summary': change_summary,
            'is_significant_change': is_significant,
            'highlight_changes': is_significant,
        }
    
    def show_final(self, text: str, stability: float = 1.0) -> dict:
        """
        Show final text (stable, black bold).
        
        Handles transition from draft to final with optional highlighting
        of changes.
        
        Args:
            text: Final text to display
            stability: Should be 1.0 for final
            
        Returns:
            Display format with transition info
        """
        # Get previous text for comparison
        previous_text = ""
        if self._current_state and not self._current_state.is_final:
            previous_text = self._current_state.text
        
        # Compute diff from last draft
        if previous_text:
            diff = self._diff_visualizer.compute_diff(previous_text, text)
            change_summary = self._diff_visualizer.get_change_summary(diff)
        else:
            diff = []
            change_summary = {'added': 0, 'removed': 0, 'same': 0, 'change_ratio': 0}
        
        # Update state
        self._previous_state = self._current_state
        self._current_state = DisplayState(
            text=text,
            is_final=True,
            stability=stability,
            timestamp=time.time()
        )
        
        self._final_shows += 1
        self._total_transitions += 1
        
        # Determine transition type
        if change_summary['change_ratio'] < 0.2:
            transition = 'smooth'  # Minor changes, fade transition
        elif change_summary['change_ratio'] < 0.5:
            transition = 'moderate'  # Some changes, highlight differences
        else:
            transition = 'significant'  # Major changes, flash highlight
        
        logger.info(
            f"Final: '{text[:40]}...' "
            f"(transition: {transition}, "
            f"changes: +{change_summary['added']}/-{change_summary['removed']})"
        )
        
        return {
            'text': text,
            'style': 'final',
            'color': 'black',
            'font_weight': 'bold',
            'stability_indicator': '✓',  # Always stable
            'opacity': 1.0,
            'diff': diff,
            'change_summary': change_summary,
            'transition_type': transition,
            'previous_text': previous_text,
        }
    
    def _get_stability_indicator(self, stability: float) -> str:
        """Get visual indicator for stability level."""
        if stability < self.STABILITY_LOW:
            return "●"  # Unstable
        elif stability < self.STABILITY_MEDIUM:
            return "○"  # Stabilizing
        else:
            return "✓"  # Stable
    
    def _get_stability_opacity(self, stability: float) -> float:
        """Get opacity based on stability (0.3-1.0)."""
        # Map 0.0-1.0 stability to 0.3-1.0 opacity
        return 0.3 + (stability * 0.7)
    
    def get_transition_animation(self, duration_ms: float = 300) -> dict:
        """
        Get animation parameters for draft→final transition.
        
        Args:
            duration_ms: Animation duration in milliseconds
            
        Returns:
            Animation parameters
        """
        if not self._current_state or not self._previous_state:
            return {'type': 'none'}
        
        # Draft → Final transition
        if not self._previous_state.is_final and self._current_state.is_final:
            # Check if significant changes
            diff = self._diff_visualizer.compute_diff(
                self._previous_state.text,
                self._current_state.text
            )
            summary = self._diff_visualizer.get_change_summary(diff)
            
            if summary['change_ratio'] > 0.3:
                # Significant change - flash highlight
                return {
                    'type': 'flash_highlight',
                    'duration_ms': duration_ms,
                    'highlight_words': [w for w, s in diff if s == 'added'],
                }
            else:
                # Minor change - smooth fade
                return {
                    'type': 'fade_transition',
                    'duration_ms': duration_ms,
                    'from_style': 'draft',
                    'to_style': 'final',
                }
        
        # Draft → Draft update
        elif not self._previous_state.is_final and not self._current_state.is_final:
            return {
                'type': 'update',
                'duration_ms': duration_ms // 2,  # Faster for drafts
            }
        
        return {'type': 'none'}
    
    def get_stats(self) -> dict:
        """Get UI statistics."""
        return {
            'draft_updates': self._draft_updates,
            'final_shows': self._final_shows,
            'total_transitions': self._total_transitions,
        }
    
    def print_stats(self):
        """Print UI statistics."""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 STREAMING UI STATS (Phase 1.4)")
        print("=" * 60)
        
        print(f"\n  Draft Updates:      {stats['draft_updates']}")
        print(f"  Final Shows:        {stats['final_shows']}")
        print(f"  Total Transitions:  {stats['total_transitions']}")
        
        if stats['final_shows'] > 0:
            avg_drafts = stats['draft_updates'] / stats['final_shows']
            print(f"\n  Avg Drafts/Final:   {avg_drafts:.1f}")
        
        print("=" * 60)


class ConsoleStreamingUI(StreamingUI):
    """
    Console-based implementation of StreamingUI for testing.
    
    Displays streaming translation in terminal with ANSI colors.
    """
    
    # ANSI color codes
    GREY = '\033[90m'
    BLACK = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    
    def show_draft(self, text: str, stability: float = 0.0):
        """Show draft in console."""
        result = super().show_draft(text, stability)
        
        indicator = result['stability_indicator']
        opacity = result['opacity']
        
        # Grey italic with opacity simulation
        print(f"\n  {self.GREY}{self.ITALIC}{text}{self.RESET}")
        print(f"     {indicator} Draft (stability: {stability:.1f})")
        
        return result
    
    def update_draft(self, new_text: str, stability: float = 0.0) -> dict:
        """Update draft in console with diff."""
        result = super().update_draft(new_text, stability)
        
        if result.get('highlight_changes'):
            # Show with change highlighting
            diff_str = self._format_diff_console(result['diff'])
            print(f"\n  {self.GREY}{self.ITALIC}{diff_str}{self.RESET}")
        else:
            print(f"\n  {self.GREY}{self.ITALIC}{new_text}{self.RESET}")
        
        indicator = result['stability_indicator']
        print(f"     {indicator} Updated (stability: {stability:.1f})")
        
        return result
    
    def show_final(self, text: str, stability: float = 1.0) -> dict:
        """Show final in console with transition."""
        result = super().show_final(text, stability)
        
        transition = result['transition_type']
        
        if transition == 'significant':
            # Flash highlight for significant changes
            print(f"\n  {self.YELLOW}{self.BOLD}✨ {text}{self.RESET}")
            print(f"     ✓ Final (significant changes from draft)")
        elif transition == 'moderate':
            # Highlight added words
            diff_str = self._format_diff_console(result['diff'])
            print(f"\n  {self.BOLD}{diff_str}{self.RESET}")
            print(f"     ✓ Final (some changes from draft)")
        else:
            # Smooth transition
            print(f"\n  {self.BOLD}{text}{self.RESET}")
            print(f"     ✓ Final")
        
        return result
    
    def _format_diff_console(self, diff: List[Tuple[str, str]]) -> str:
        """Format diff for console display."""
        parts = []
        
        for word, status in diff:
            if status == 'same':
                parts.append(word)
            elif status == 'added':
                # Highlight added words
                parts.append(f"{self.YELLOW}{word}{self.GREY}")
            # Skip removed words
        
        return ' '.join(parts)


def demo_streaming_ui():
    """Demo the streaming UI in console."""
    print("\n" + "=" * 70)
    print(" " * 20 + "STREAMING UI DEMO")
    print("=" * 70)
    
    ui = ConsoleStreamingUI()
    
    print("\n--- Simulating Translation Session ---\n")
    
    # Draft 1
    print("T=0s: First draft")
    ui.show_draft("Hello...", stability=0.0)
    
    # Draft 2
    print("\nT=2s: Draft update")
    ui.update_draft("Hello world...", stability=0.6)
    
    # Draft 3
    print("\nT=4s: Another update")
    ui.update_draft("Hello world today...", stability=0.8)
    
    # Final (minor change)
    print("\nT=5s: Final (minor changes)")
    ui.show_final("Hello world today.", stability=1.0)
    
    print("\n" + "-" * 70)
    print("\n--- Simulating Session with Significant Changes ---\n")
    
    # Draft
    ui2 = ConsoleStreamingUI()
    print("Draft:")
    ui2.show_draft("I want to go...", stability=0.5)
    
    # Final (significant change)
    print("\nFinal (significant change from draft):")
    ui2.show_final("I went to the store yesterday.", stability=1.0)
    
    print("\n" + "=" * 70)
    ui.print_stats()


if __name__ == "__main__":
    demo_streaming_ui()
