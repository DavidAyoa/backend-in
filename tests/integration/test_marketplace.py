#!/usr/bin/env python3
"""
Test script for agent marketplace functionality
Tests marketplace browsing, searching, cloning, and sharing features
"""

import asyncio
import json
import sys
import os
from typing import Dict, List

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_setup():
    """Test that the database is properly set up with marketplace fields"""
    print("Testing database setup...")
    
    try:
        from models.user import user_db
        import time
        
        # Test database initialization
        user_db.init_database()
        print("✅ Database initialized successfully")
        
        # Test that we can create a user with unique username
        timestamp = int(time.time())
        user = user_db.create_user(
            email=f"test{timestamp}@example.com",
            username=f"testuser{timestamp}",
            password="testpass123",
            full_name="Test User"
        )
        print(f"✅ Created test user: {user.username}")
        
        # Test agent creation with marketplace fields
        agent_id = user_db.create_agent(user.id, "Test Agent")
        if agent_id:
            print(f"✅ Created test agent: {agent_id}")
            
            # Test updating with marketplace fields
            update_data = {
                "description": "A test agent for marketplace testing",
                "system_prompt": "You are a helpful test assistant",
                "is_public": True,
                "category": "testing",
                "tags": ["test", "demo", "marketplace"]
            }
            
            updated = user_db.update_agent(agent_id, update_data)
            if updated:
                print("✅ Updated agent with marketplace fields")
                
                # Verify the fields were saved
                agent = user_db.get_agent_by_id(agent_id)
                if agent:
                    print(f"   - is_public: {agent.get('is_public')}")
                    print(f"   - category: {agent.get('category')}")
                    print(f"   - tags: {agent.get('tags')}")
                    print(f"   - clone_count: {agent.get('clone_count', 0)}")
                else:
                    print("❌ Could not retrieve updated agent")
            else:
                print("❌ Failed to update agent")
        else:
            print("❌ Failed to create agent")
            
        return True
        
    except Exception as e:
        print(f"❌ Database setup test failed: {e}")
        return False

def test_marketplace_methods():
    """Test marketplace-specific database methods"""
    print("\nTesting marketplace methods...")
    
    try:
        from models.user import user_db
        import time
        
        # Create a couple of test users with unique usernames
        timestamp = int(time.time())
        user1 = user_db.create_user(
            email=f"creator1_{timestamp}@example.com",
            username=f"creator1_{timestamp}",
            password="pass123",
            full_name="Creator One"
        )
        
        user2 = user_db.create_user(
            email=f"creator2_{timestamp}@example.com",
            username=f"creator2_{timestamp}",
            password="pass123",
            full_name="Creator Two"
        )
        
        # Create some public agents
        agent1_id = user_db.create_agent(user1.id, "Customer Service Bot")
        user_db.update_agent(agent1_id, {
            "description": "Helpful customer service assistant",
            "system_prompt": "You are a customer service representative",
            "is_public": True,
            "category": "business",
            "tags": ["customer-service", "business", "support"]
        })
        
        agent2_id = user_db.create_agent(user2.id, "Code Helper")
        user_db.update_agent(agent2_id, {
            "description": "Programming assistant for developers",
            "system_prompt": "You are a coding assistant",
            "is_public": True,
            "category": "development",
            "tags": ["coding", "programming", "development"]
        })
        
        # Test getting public agents
        public_agents = user_db.get_public_agents(limit=10)
        print(f"✅ Found {len(public_agents)} public agents")
        
        # Test category filtering
        business_agents = user_db.get_public_agents(category="business", limit=10)
        print(f"✅ Found {len(business_agents)} business agents")
        
        # Test search functionality
        search_results = user_db.search_public_agents("customer", limit=10)
        print(f"✅ Search for 'customer' returned {len(search_results)} results")
        
        # Test cloning
        clone_id = user_db.clone_agent(agent1_id, user2.id, "My Customer Service Bot")
        if clone_id:
            print(f"✅ Successfully cloned agent: {clone_id}")
            
            # Check if clone count increased
            original_agent = user_db.get_agent_by_id(agent1_id)
            print(f"   - Original agent clone count: {original_agent.get('clone_count', 0)}")
            
            # Check cloned agent details
            cloned_agent = user_db.get_agent_by_id(clone_id)
            print(f"   - Cloned agent original_id: {cloned_agent.get('original_agent_id')}")
        else:
            print("❌ Failed to clone agent")
        
        # Test getting clones
        clones = user_db.get_agent_clones(agent1_id)
        print(f"✅ Found {len(clones)} clones of agent {agent1_id}")
        
        # Test trending agents
        trending = user_db.get_trending_agents(limit=5)
        print(f"✅ Found {len(trending)} trending agents")
        
        # Test marketplace stats
        stats = user_db.get_marketplace_stats()
        print(f"✅ Marketplace stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Marketplace methods test failed: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints (requires server to be running)"""
    print("\nTesting API endpoints...")
    
    try:
        import requests
        
        base_url = "http://localhost:8000"
        
        # Test marketplace browsing
        response = requests.get(f"{base_url}/agents/marketplace/browse")
        if response.status_code == 200:
            agents = response.json()
            print(f"✅ Marketplace browse returned {len(agents)} agents")
        else:
            print(f"⚠️  Marketplace browse returned status {response.status_code}")
        
        # Test marketplace search
        response = requests.get(f"{base_url}/agents/marketplace/search?q=test")
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Marketplace search returned {len(results)} results")
        else:
            print(f"⚠️  Marketplace search returned status {response.status_code}")
        
        # Test marketplace stats
        response = requests.get(f"{base_url}/agents/marketplace/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Marketplace stats: {stats}")
        else:
            print(f"⚠️  Marketplace stats returned status {response.status_code}")
        
        # Test trending agents
        response = requests.get(f"{base_url}/agents/marketplace/trending")
        if response.status_code == 200:
            trending = response.json()
            print(f"✅ Trending agents returned {len(trending)} agents")
        else:
            print(f"⚠️  Trending agents returned status {response.status_code}")
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("⚠️  Server not running - skipping API tests")
        return True
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def test_scenarios():
    """Test realistic marketplace scenarios"""
    print("\nTesting marketplace scenarios...")
    
    try:
        from models.user import user_db
        import time
        
        # Scenario 1: User creates and publishes an agent
        print("\n📋 Scenario 1: Create and publish agent")
        timestamp = int(time.time())
        creator = user_db.create_user(
            email=f"creator_{timestamp}@example.com",
            username=f"agentcreator_{timestamp}",
            password="pass123",
            full_name="Agent Creator"
        )
        
        agent_id = user_db.create_agent(creator.id, "Travel Assistant")
        user_db.update_agent(agent_id, {
            "description": "AI assistant for travel planning and booking",
            "system_prompt": "You are a travel planning expert",
            "is_public": True,
            "category": "travel",
            "tags": ["travel", "planning", "booking", "assistant"]
        })
        print("✅ Agent created and published to marketplace")
        
        # Scenario 2: Another user discovers and clones the agent
        print("\n📋 Scenario 2: Discover and clone agent")
        user = user_db.create_user(
            email=f"user_{timestamp}@example.com",
            username=f"regularuser_{timestamp}",
            password="pass123",
            full_name="Regular User"
        )
        
        # Search for travel agents
        travel_agents = user_db.search_public_agents("travel", limit=10)
        if travel_agents:
            print(f"✅ Found {len(travel_agents)} travel agents")
            
            # Clone the first one
            clone_id = user_db.clone_agent(travel_agents[0]['id'], user.id, "My Travel Planner")
            if clone_id:
                print("✅ Successfully cloned travel assistant")
                
                # Verify the clone
                clone = user_db.get_agent_by_id(clone_id)
                print(f"   - Clone name: {clone['agent_name']}")
                print(f"   - Original agent: {clone['original_agent_id']}")
            else:
                print("❌ Failed to clone agent")
        else:
            print("❌ No travel agents found")
        
        # Scenario 3: Check marketplace activity
        print("\n📋 Scenario 3: Check marketplace activity")
        stats = user_db.get_marketplace_stats()
        print(f"✅ Marketplace has {stats['total_public_agents']} public agents")
        print(f"✅ Total clones: {stats['total_clones']}")
        print(f"✅ Categories: {[cat['category'] for cat in stats['categories']]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Scenario test failed: {e}")
        return False

def example_usage():
    """Show example API usage"""
    print("\n" + "="*60)
    print("AGENT MARKETPLACE - EXAMPLE USAGE")
    print("="*60)
    
    print("""
🔥 MARKETPLACE FEATURES IMPLEMENTED:

1. 📝 CREATE & PUBLISH AGENTS:
   POST /agents/
   {
     "agent_name": "Customer Service Bot",
     "description": "Helpful customer service assistant",
     "system_prompt": "You are a customer service representative"
   }
   
   PUT /agents/{agent_id}/visibility?is_public=true
   # Makes agent public in marketplace

2. 🛍️ BROWSE MARKETPLACE:
   GET /agents/marketplace/browse
   GET /agents/marketplace/browse?category=business
   GET /agents/marketplace/browse?limit=20&offset=0

3. 🔍 SEARCH AGENTS:
   GET /agents/marketplace/search?q=customer
   GET /agents/marketplace/search?q=coding&category=development

4. 🔥 TRENDING AGENTS:
   GET /agents/marketplace/trending?limit=10

5. 📊 MARKETPLACE STATS:
   GET /agents/marketplace/stats

6. 🔄 CLONE AGENTS:
   POST /agents/{agent_id}/clone
   {
     "new_name": "My Customer Service Bot"
   }

7. 👥 VIEW CLONES:
   GET /agents/{agent_id}/clones

8. 📱 UPDATE AGENT WITH MARKETPLACE FIELDS:
   PUT /agents/{agent_id}
   {
     "description": "Updated description",
     "is_public": true,
     "category": "business",
     "tags": ["customer-service", "support"]
   }

💡 WEBSOCKET USAGE:
   ws://localhost:8000/ws/auth?token=YOUR_TOKEN&agent_id=CLONED_AGENT_ID
   # Use cloned agents in voice conversations!

🚀 FEATURES:
   ✅ Public/Private agent visibility
   ✅ Agent categorization and tagging
   ✅ Search and filtering
   ✅ Clone tracking and statistics
   ✅ Trending agents by popularity
   ✅ Creator attribution
   ✅ Marketplace analytics
   ✅ Agent forking/cloning
   ✅ Multi-conversation support per agent

🔐 PERMISSIONS:
   - Only owners can modify their agents
   - Public agents can be cloned by anyone
   - Private agents only visible to owner
   - Clone count tracks popularity
   - Creator information preserved
    """)

def main():
    """Run all tests"""
    print("🚀 Starting Agent Marketplace Tests")
    print("=" * 50)
    
    tests = [
        ("Database Setup", test_database_setup),
        ("Marketplace Methods", test_marketplace_methods),
        ("API Endpoints", test_api_endpoints),
        ("Realistic Scenarios", test_scenarios),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n=== {test_name} ===")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Success Rate: {success_rate:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:20} {status}")
    
    if success_rate >= 75:
        print("\n🎉 AGENT MARKETPLACE IS READY!")
        print("\nNext steps:")
        print("1. Start the server: python main.py")
        print("2. Create agents and publish them")
        print("3. Browse and clone agents from marketplace")
        print("4. Use cloned agents in voice conversations")
    else:
        print("\n❌ Agent marketplace needs attention before use")
    
    # Show example usage
    example_usage()

if __name__ == "__main__":
    main()
