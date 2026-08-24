    def check_balance(self, state: AccountState) -> Optional[int]:
        """Check account balance using 'owo cash' command"""
        try:
            api = state.session
            
            # Send balance check command
            if not api.send_message(config.CHANNEL_ID, config.BALANCE_CHECK_COMMAND):
                return None
            
            # Wait for bot to respond
            time.sleep(config.MESSAGE_WAIT_TIMEOUT)
            messages = api.get_messages(config.CHANNEL_ID, limit=10)
            
            # Find response from OwO bot (most recent message)
            if not messages:
                logger.warning(f"{cyan(f'[{state.user_id}]')} No messages found in channel")
                return None
            
            logger.debug(f"{cyan(f'[{state.user_id}]')} Checking {len(messages)} messages...")
            
            for msg in messages:
                author_id = msg.get('author', {}).get('id')
                content = msg.get('content', '')
                logger.debug(f"{cyan(f'[{state.user_id}]')} Message from {author_id}: {content[:100]}")
                
                if author_id == config.OWO_BOT_ID:
                    balance = parse_balance(content)
                    if balance is not None:
                        logger.info(f"{cyan(f'[{state.user_id}]')} Found balance: {balance}")
                        return balance
            
            logger.warning(f"{cyan(f'[{state.user_id}]')} OwO bot message not found or could not parse balance")
            logger.warning(f"{cyan(f'[{state.user_id}]')} Expected bot ID: {config.OWO_BOT_ID}")
            return None
        
        except Exception as e:
            logger.error(f"{cyan(f'[{state.user_id}]')} Error checking balance: {e}")
            return None
