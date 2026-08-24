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
            
            logger.info(f"{cyan(f'[{state.user_id}]')} Fetched {len(messages)} messages from channel")
            
            # Find response from OwO bot (most recent message)
            if not messages:
                logger.warning(f"{cyan(f'[{state.user_id}]')} No messages found in channel")
                return None
            
            logger.info(f"{cyan(f'[{state.user_id}]')} Expected OWO_BOT_ID: {config.OWO_BOT_ID}")
            
            for i, msg in enumerate(messages):
                author_id = msg.get('author', {}).get('id')
                author_name = msg.get('author', {}).get('username', 'Unknown')
                content = msg.get('content', '')
                logger.info(f"{cyan(f'[{state.user_id}]')} Message {i}: Author ID={author_id} ({author_name}), Content: {content[:80]}")
                
                # Check if this is from OwO bot
                if str(author_id) == str(config.OWO_BOT_ID):
                    logger.info(f"{cyan(f'[{state.user_id}]')} Found OwO bot message!")
                    balance = parse_balance(content)
                    if balance is not None:
                        logger.info(f"{cyan(f'[{state.user_id}]')} Successfully parsed balance: {balance}")
                        return balance
                    else:
                        logger.warning(f"{cyan(f'[{state.user_id}]')} Could not parse balance from: {content}")
            
            logger.warning(f"{cyan(f'[{state.user_id}]')} No message found from bot ID {config.OWO_BOT_ID}")
            return None
        
        except Exception as e:
            logger.error(f"{cyan(f'[{state.user_id}]')} Error checking balance: {e}", exc_info=True)
            return None
