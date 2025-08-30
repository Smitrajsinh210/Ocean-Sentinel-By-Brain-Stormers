"""
Ocean Sentinel - Blockchain Data Integrity Service
Starton platform integration for immutable data logging
"""

import asyncio
import aiohttp
import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from app.config import settings, API_CONFIG
from app.utils.database import create_supabase_client

logger = logging.getLogger(__name__)

class BlockchainService:
    """Blockchain data integrity service using Starton platform"""
    
    def __init__(self):
        self.supabase = create_supabase_client()
        self.starton_api_key = settings.starton_api_key
        self.contract_address = settings.contract_address
        self.network = settings.polygon_network
        self.base_url = API_CONFIG['starton']['base_url']
        
        # Headers for Starton API
        self.headers = {
            'x-api-key': self.starton_api_key,
            'Content-Type': 'application/json'
        }
    
    async def log_environmental_data(
        self, 
        data_hash: str, 
        timestamp: str, 
        source: str
    ) -> Optional[str]:
        """
        Log environmental data hash to blockchain
        Args:
            data_hash: SHA-256 hash of environmental data
            timestamp: ISO timestamp of data collection
            source: Data source identifier
        Returns:
            Transaction hash if successful
        """
        try:
            logger.info(f"📝 Logging environmental data to blockchain: {source}")
            
            # Prepare transaction data
            function_name = "logEnvironmentalData"
            params = [data_hash, timestamp, source]
            
            # Execute smart contract function
            tx_hash = await self._execute_contract_function(function_name, params)
            
            if tx_hash:
                # Store blockchain transaction record
                await self._store_blockchain_record(
                    tx_hash, data_hash, timestamp, source, 'environmental_data'
                )
                
                logger.info(f"✅ Environmental data logged to blockchain: {tx_hash}")
                return tx_hash
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to log environmental data to blockchain: {e}")
            return None
    
    async def log_threat_data(self, threat_data: Dict, threat_id: str) -> Optional[str]:
        """
        Log threat detection to blockchain
        Args:
            threat_data: Threat detection data
            threat_id: Unique threat identifier
        Returns:
            Transaction hash if successful
        """
        try:
            logger.info(f"🚨 Logging threat data to blockchain: {threat_data.get('type')}")
            
            # Create hash of threat data
            threat_hash = self._create_data_hash(threat_data)
            
            # Prepare transaction data
            function_name = "logThreatData"
            params = [
                threat_id,
                threat_hash,
                threat_data.get('type', 'unknown'),
                threat_data.get('severity', 1),
                int(threat_data.get('confidence', 0) * 100),  # Convert to percentage
                datetime.utcnow().isoformat()
            ]
            
            # Execute smart contract function
            tx_hash = await self._execute_contract_function(function_name, params)
            
            if tx_hash:
                # Store blockchain transaction record
                await self._store_blockchain_record(
                    tx_hash, threat_hash, datetime.utcnow().isoformat(), 
                    'ai_detection', 'threat_data', threat_id
                )
                
                logger.info(f"✅ Threat data logged to blockchain: {tx_hash}")
                return tx_hash
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to log threat data to blockchain: {e}")
            return None
    
    async def verify_data_integrity(self, data_hash: str) -> Dict[str, Any]:
        """
        Verify data integrity using blockchain records
        Args:
            data_hash: Hash to verify
        Returns:
            Verification result with details
        """
        try:
            logger.info(f"🔍 Verifying data integrity: {data_hash[:16]}...")
            
            # Query smart contract for verification
            function_name = "verifyDataIntegrity"
            params = [data_hash]
            
            # Read from smart contract
            result = await self._read_contract_function(function_name, params)
            
            if result:
                verification_result = {
                    'verified': result.get('verified', False),
                    'timestamp': result.get('timestamp'),
                    'source': result.get('source'),
                    'block_number': result.get('blockNumber'),
                    'transaction_hash': result.get('transactionHash')
                }
                
                logger.info(f"✅ Data verification completed: {verification_result['verified']}")
                return verification_result
            
            return {'verified': False, 'error': 'No blockchain record found'}
            
        except Exception as e:
            logger.error(f"❌ Data verification failed: {e}")
            return {'verified': False, 'error': str(e)}
    
    async def get_audit_trail(
        self, 
        start_date: str, 
        end_date: str, 
        data_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail of blockchain transactions
        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            data_type: Optional filter by data type
        Returns:
            List of blockchain transactions
        """
        try:
            logger.info(f"📋 Retrieving audit trail: {start_date} to {end_date}")
            
            # Get events from smart contract
            events = await self._get_contract_events(start_date, end_date)
            
            # Filter by data type if specified
            if data_type:
                events = [e for e in events if e.get('data_type') == data_type]
            
            # Enhance with database records
            enhanced_events = []
            for event in events:
                db_record = await self._get_blockchain_record(event.get('transactionHash'))
                if db_record:
                    event.update(db_record)
                enhanced_events.append(event)
            
            logger.info(f"✅ Retrieved {len(enhanced_events)} audit trail records")
            return enhanced_events
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve audit trail: {e}")
            return []
    
    async def _execute_contract_function(
        self, 
        function_name: str, 
        params: List
    ) -> Optional[str]:
        """Execute a smart contract function via Starton"""
        try:
            url = f"{self.base_url}/smart-contract/{self.network}/{self.contract_address}/call"
            
            payload = {
                "functionName": function_name,
                "params": params,
                "signerWallet": await self._get_signer_wallet(),
                "speed": "average"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=self.headers, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 201:
                        result = await response.json()
                        return result.get('transactionHash')
                    else:
                        error_text = await response.text()
                        logger.error(f"Starton API error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Contract execution error: {e}")
            return None
    
    async def _read_contract_function(
        self, 
        function_name: str, 
        params: List
    ) -> Optional[Dict]:
        """Read from a smart contract function via Starton"""
        try:
            url = f"{self.base_url}/smart-contract/{self.network}/{self.contract_address}/read"
            
            payload = {
                "functionName": function_name,
                "params": params
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=self.headers, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Contract read error {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Contract read error: {e}")
            return None
    
    async def _get_contract_events(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """Get events from smart contract"""
        try:
            url = f"{self.base_url}/smart-contract/{self.network}/{self.contract_address}/events"
            
            params = {
                'fromBlock': 'earliest',
                'toBlock': 'latest',
                'limit': 1000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers, 
                    params=params
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return data.get('items', [])
                    else:
                        logger.error(f"Events fetch error {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Events fetch error: {e}")
            return []
    
    async def _get_signer_wallet(self) -> str:
        """Get or create signer wallet address for transactions"""
        try:
            # In production, this would be a secure wallet management system
            # For demo, we'll use a test wallet
            return "0x742d35Cc6634C0532925a3b8D395DBFAF4fB8fE4"  # Test wallet
            
        except Exception as e:
            logger.error(f"Error getting signer wallet: {e}")
            return ""
    
    async def _store_blockchain_record(
        self, 
        tx_hash: str, 
        data_hash: str, 
        timestamp: str, 
        source: str, 
        data_type: str,
        reference_id: Optional[str] = None
    ):
        """Store blockchain transaction record in database"""
        try:
            record = {
                'transaction_hash': tx_hash,
                'data_hash': data_hash,
                'timestamp': timestamp,
                'source': source,
                'data_type': data_type,
                'reference_id': reference_id,
                'network': self.network,
                'contract_address': self.contract_address,
                'created_at': datetime.utcnow().isoformat()
            }
            
            await self.supabase.table('blockchain_transactions').insert(record).execute()
            logger.info(f"📝 Blockchain record stored: {tx_hash}")
            
        except Exception as e:
            logger.error(f"Failed to store blockchain record: {e}")
    
    async def _get_blockchain_record(self, tx_hash: str) -> Optional[Dict]:
        """Get blockchain transaction record from database"""
        try:
            result = await self.supabase.table('blockchain_transactions')\
                .select('*')\
                .eq('transaction_hash', tx_hash)\
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get blockchain record: {e}")
            return None
    
    def _create_data_hash(self, data: Any) -> str:
        """Create SHA-256 hash of data"""
        try:
            if isinstance(data, dict):
                data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
            else:
                data_str = str(data)
            
            return hashlib.sha256(data_str.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error creating data hash: {e}")
            return hashlib.sha256(str(data).encode()).hexdigest()
    
    async def get_blockchain_statistics(self) -> Dict[str, Any]:
        """Get blockchain usage statistics"""
        try:
            result = await self.supabase.table('blockchain_transactions')\
                .select('*', count='exact')\
                .execute()
            
            total_transactions = result.count
            
            # Get counts by data type
            type_counts = await self.supabase.rpc(
                'get_blockchain_stats_by_type'
            ).execute()
            
            return {
                'total_transactions': total_transactions,
                'network': self.network,
                'contract_address': self.contract_address,
                'transactions_by_type': type_counts.data if type_counts.data else {},
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting blockchain statistics: {e}")
            return {
                'total_transactions': 0,
                'error': str(e)
            }
