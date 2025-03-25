"""
Event emitter utility for handling event subscriptions and notifications
"""

import asyncio
from typing import Dict, List, Any

class EventEmitter:
    """
    A simple event emitter for handling event subscriptions and notifications
    """

    def __init__(self):
        """Initialize the event emitter"""
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}

    async def subscribe(self, event_type: str) -> asyncio.Queue:
        """
        Subscribe to an event type
        
        Args:
            event_type: The type of event to subscribe to
            
        Returns:
            A queue that will receive events of the specified type
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
            
        queue = asyncio.Queue()
        self.subscribers[event_type].append(queue)
        return queue

    async def unsubscribe(self, event_type: str, queue: asyncio.Queue) -> None:
        """
        Unsubscribe from an event type
        
        Args:
            event_type: The type of event to unsubscribe from
            queue: The queue to remove from subscribers
        """
        if event_type in self.subscribers and queue in self.subscribers[event_type]:
            self.subscribers[event_type].remove(queue)

    async def emit(self, event_type: str, data: Any) -> None:
        """
        Emit an event to all subscribers
        
        Args:
            event_type: The type of event to emit
            data: The data to send to subscribers
        """
        if event_type not in self.subscribers:
            return

        for queue in self.subscribers[event_type]:
            try:
                await queue.put(data)
            except Exception as e:
                # Log error but continue with other subscribers
                print(f"Error emitting event to subscriber: {e}")

    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get the number of subscribers for an event type
        
        Args:
            event_type: The type of event to count subscribers for
            
        Returns:
            The number of subscribers for the event type
        """
        return len(self.subscribers.get(event_type, [])) 